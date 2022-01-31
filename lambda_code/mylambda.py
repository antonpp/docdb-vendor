import boto3
import pymongo
import os


secret_name = os.environ.get('secret_name')
region_name = os.environ.get('region_name')
docdb_cluster_id = os.environ.get('docdb_cluster_id')
docdb_username = os.environ.get('docdb_username')


sm = boto3.client("secretsmanager", region_name=region_name)
docdb = boto3.client("docdb", region_name=region_name)

def handler(event, context):
    print("Secret name is {}".format(secret_name))
    pwd = sm.get_secret_value(SecretId=secret_name)
    clusters = docdb.describe_db_clusters()["DBClusters"]
    docdb_clusters = list(filter(lambda o: o["DBClusterIdentifier"] == docdb_cluster_id, clusters))
    if len(docdb_clusters) != 1: raise Exception("Failed to find the DocumentDB cluster with id {}".format(docdb_cluster_id))

    docdb_endpoint = docdb_clusters[0]["Endpoint"]
    docdb_password = pwd["SecretString"]

    print("Fetching secrets...")
    print("docdb password: {}".format(docdb_password))
    print("docdb endpoint: {}".format(docdb_endpoint))

    ##Create a MongoDB client, open a connection to Amazon DocumentDB as a replica set and specify the read preference as secondary preferred
    client = pymongo.MongoClient('mongodb://{username}:{password}@{endpoint}:{port}/?tls=true&tlsCAFile=rds-combined-ca-bundle.pem&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false'.format(**{
        "username": docdb_username,
        "password": docdb_password,
        "endpoint": docdb_endpoint,
        "port": 27017
    }))

    dbs = client.list_databases()
    print("Found databases: {}".format(list(dbs)))

    client.close()
    return None