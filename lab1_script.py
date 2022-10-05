# Keys are defined in configuration file, do we need to do anything else??
import boto3
import json
import time
import subprocess
from multiprocessing import Pool
import time

start_time = time.time()
ec2_client = boto3.client("ec2")
ec2 = boto3.resource('ec2')



def createInstances(ec2, INSTANCE_TYPE, COUNT, SECURITY_GROUP, SUBNET_ID):
    # Don't change these
    KEY_NAME = "vockey"
    INSTANCE_IMAGE = "ami-08d4ac5b634553e16"

    return ec2.create_instances(
        ImageId=INSTANCE_IMAGE,
        MinCount=COUNT,
        MaxCount=COUNT,
        InstanceType=INSTANCE_TYPE,
        KeyName=KEY_NAME,
        SecurityGroupIds=SECURITY_GROUP,
        SubnetId = SUBNET_ID
    )

def terminateAll(ec2_client):
    # DOES NOT WORK YET
    groups = ec2_client.describe_security_groups()
    vpc_id = groups["SecurityGroups"][0]["VpcId"]
    instance_ids = [instance.id for instance in ec2.instances]
    instance_data_raw = ec2_client.describe_instances(InstanceIds=instance_ids)

    # Get the id's of all running ec2 clients
    ins_ids_terminate = []
    for res_id in range(len(instance_data_raw["Reservations"])):
        for ins_id in range(len(instance_data_raw["Reservations"][res_id]["Instances"])):
            ins_ids_terminate.append(instance_data_raw["Reservations"][res_id]["Instances"][ins_id]["PublicIpAddress"])
    ec2_client.terminate_instances(InstanceIds=(ins_ids_terminate))

    # Wait for all instances to be terminated (else security group will not be deleted)
    instance_terminated_waiter = ec2_client.get_waiter('instance_terminated')
    instance_terminated_waiter.wait(InstanceIds=(ins_ids_terminate))

    # Now remove the security group as well!
    # Did not find a waiter for this
    ec2_client.delete_security_group(
        Description="SSH all",
        GroupName="Cloud Computing TP1",
        VpcId=vpc_id
    )




def main(ec2_client, ec2):
    # CODE TO CREATE INSTANCES STARTS HERE
    # First remove any running instances and/or security groups

    # Creating 10 instances 

    # Create security group, using only SSH access available from anywhere
    groups = ec2_client.describe_security_groups()
    vpc_id = groups["SecurityGroups"][0]["VpcId"]


    new_group = ec2_client.create_security_group(
        Description="SSH all",
        GroupName="Cloud Computing TP1",
        VpcId=vpc_id
    )

    # Wait for the security group to exist!
    new_group_waiter = ec2_client.get_waiter('security_group_exists')
    new_group_waiter.wait(GroupNames=["Cloud Computing TP1"])


    group_id = new_group["GroupId"]

    rule_creation = ec2_client.authorize_security_group_ingress(
        GroupName="Cloud Computing TP1",
        GroupId=group_id,
        IpPermissions=[{
            'FromPort': 22,
            'ToPort': 22,
            'IpProtocol': 'tcp',
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
        }]
    )

    SECURITY_GROUP = [group_id]

    print(SECURITY_GROUP)

    # Availability zones

    response = ec2_client.describe_subnets()

    availabilityzones = {}
    for subnet in response.get('Subnets'):
            #print(subnet)
            availabilityzones.update({subnet.get('AvailabilityZone'): subnet.get('SubnetId')})

    #print(availabilityzones)

    # Get wanted availability zone
    availability_zone_1a = availabilityzones.get('us-east-1a')
    availability_zone_1b = availabilityzones.get('us-east-1b')
    availability_zone_1c = availabilityzones.get('us-east-1c')

    print(availability_zone_1a)

    # Types: t2.large and m4.large, testing with micro

    instances_t2_a = createInstances(ec2, "t2.large", 2, SECURITY_GROUP,availability_zone_1a)
    instances_m4_a = createInstances(ec2, "m4.large", 2, SECURITY_GROUP,availability_zone_1a)
    instances_t2_b = createInstances(ec2, "t2.large", 2, SECURITY_GROUP,availability_zone_1b)
    instances_m4_b = createInstances(ec2, "m4.large", 2, SECURITY_GROUP,availability_zone_1b)
    instances_t2_c = createInstances(ec2, "t2.large", 1, SECURITY_GROUP,availability_zone_1c)


    # print(instances_t2_a)

    instance_ids = []

    for instance in instances_t2_a:
        instance_ids.append(instance.id)

    for instance in instances_m4_a:
        instance_ids.append(instance.id)

    for instance in instances_t2_b:
        instance_ids.append(instance.id)

    for instance in instances_m4_b:
        instance_ids.append(instance.id)

    for instance in instances_t2_c:
        instance_ids.append(instance.id)

    # Wait for all instances to be active!
    instance_running_waiter = ec2_client.get_waiter('instance_running')
    instance_running_waiter.wait(InstanceIds=(instance_ids))


    return instance_ids


def values(ec2_client, instance_ids):
    instance_data_raw = ec2_client.describe_instances(InstanceIds=instance_ids)
    instance_list = instance_data_raw["Reservations"][0]["Instances"]

    # Example Get IP address
    ins_ips = []
    for res_id in range(len(instance_data_raw["Reservations"])):
        for ins_id in range(len(instance_data_raw["Reservations"][res_id]["Instances"])):
            ins_ips.append(instance_data_raw["Reservations"][res_id]["Instances"][ins_id]["PublicIpAddress"])
    print(ins_ips)
    return ins_ips

# Functions to deploy flask in parallel on the 10 instances
def pool_subprocess(ins_ips):
    pool = Pool()
    results = pool.map(call_subprocess, ins_ips)
    pool.close()
    pool.join()
    print(results)

def call_subprocess(ins_ip):
    subprocess.call(['sh', './lab1_flask.sh', ins_ip])
    print(500 * "-")
    print(str(ins_ip) + " has flask deployed!")

    return True


ins_ips = values(ec2_client, main(ec2_client, ec2))
# ins_ips = []
# Deploy in serial manner
# for i in ins_ips:
#    subprocess.call(['sh', './lab1_flask.sh', i])

# Deploy in parellel 
pool_subprocess(ins_ips)
print("--- %s seconds ---" % (time.time() - start_time))