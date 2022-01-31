from importlib.metadata import entry_points
import os.path
from tkinter import image_names
from typing_extensions import runtime

from aws_cdk.aws_s3_assets import Asset

from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_docdb as docdb,
    aws_secretsmanager as sm,
    aws_lambda as lambada,
    SecretValue, App, Stack, Environment, RemovalPolicy, BundlingOptions
)

from constructs import Construct

TARGET_VPC_NAME = "docdb-test-vpc"

dirname = os.path.dirname(__file__)
env_london = Environment(account="712464346497", region="eu-west-2")


class EC2InstanceStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # VPC
        vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_name=TARGET_VPC_NAME)

        # AMI
        amzn_linux = ec2.MachineImage.latest_amazon_linux(
            generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
            edition=ec2.AmazonLinuxEdition.STANDARD,
            virtualization=ec2.AmazonLinuxVirt.HVM,
            storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE
        )

        # Instance Role and SSM Managed Policy
        role = iam.Role(self, "InstanceSSM", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"))

        role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))

        # Instance
        instance = ec2.Instance(self, "Bastion",
            instance_type=ec2.InstanceType("t3.small"),
            machine_image=amzn_linux,
            vpc = vpc,
            role = role,
            instance_name="docdb-bastion",
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT)
        )

        # Script in S3 as Asset
        asset = Asset(self, "Asset", path=os.path.join(dirname, "configure.sh"))
        local_path = instance.user_data.add_s3_download_command(
            bucket=asset.bucket,
            bucket_key=asset.s3_object_key
        )

        # Userdata executes script from S3
        instance.user_data.add_execute_file_command(
            file_path=local_path
            )
        asset.grant_read(instance.role)

        docdb_password = sm.Secret(
            self, 
            "docdb_password", 
            generate_secret_string=sm.SecretStringGenerator(
                exclude_punctuation=True,
                include_space=False
            )
        )

        cluster = docdb.DatabaseCluster(self, "Database",
            master_user=docdb.Login(
                username=SecretValue.plain_text("myuser").to_string(),
                password=docdb_password.secret_value,
                secret_name="docdbtest"
            ),
            instance_type=ec2.InstanceType("r5.large"),
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT
            ),
            vpc=vpc,
            db_cluster_name="docdb-vended-cluster",
            instances=2,
            removal_policy=RemovalPolicy.DESTROY,
            deletion_protection=False
        )
        cluster.connections.allow_default_port_from_any_ipv4(
            "Allow connections to default port (27017)"
        )

        fn = lambada.Function(
            self, 
            "DocdbTestFunction", 
            runtime=lambada.Runtime.PYTHON_3_6,
            handler="mylambda.handler", 
            environment={
                "secret_name": docdb_password.secret_name,
                "region_name": "eu-west-2",
                "docdb_cluster_id": "docdb-vended-cluster",
                "docdb_username": "myuser"
            },
            vpc=vpc,
            code=lambada.Code.from_asset('lambda_code', bundling=BundlingOptions(
                image=lambada.Runtime.PYTHON_3_6.bundling_image,
                command=["bash", "-c", "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"]
            ))
        )
        fn.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDocDBFullAccess'))
        fn.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('SecretsManagerReadWrite'))

app = App()

EC2InstanceStack(app, "docdb-vended-stack", env=env_london)

app.synth()