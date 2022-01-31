# docdb-vendor
Amazon DocumentDB vending machine

POC of an application that deploys an Amazon DocumntDB cluster into an existing VPC defined by the user.

### What will be deployed?
A DocumentDB cluster inside the specified VPC.  
A secret will be stored in Secrets Manager containing the password of the user.  
A bastion ec2 instance with pre-installed mongo shell inside the same VPC (to test connection).  
A lambda function that will read the secret password and connect to the DocumentDB cluster.  


### To run
1. Ensure CDK is installed
```
$ npm install -g aws-cdk
```

2. Create a Python virtual environment
```
$ python3 -m venv .venv
```

3. Activate virtual environment

_On MacOS or Linux_
```
$ source .venv/bin/activate
```

_On Windows_
```
% .venv\Scripts\activate.bat
```

4. Install the required dependencies.

```
$ pip install -r requirements.txt
```

5. Synthesize (`cdk synth`) or deploy (`cdk deploy`) the example

```
$ cdk deploy
```

### Edit app.py:
update account number at top of file and the target VPC name.

### To dispose of the stack afterwards:

```
$ cdk destroy
```