import boto3
import time
import webbrowser

autoscale = boto3.client('autoscaling')
cloudwatch = boto3.client('cloudwatch')
ec2 = boto3.client('ec2')

# Security group
security_group_id = "sg-073c85e37a38f2431"

# User data
user_data = """
    #!/bin/bash
    sudo yum install -y httpd
    sudo service httpd start    
    mkdir ~/.aws && cd ~/.aws
    touch credentials && touch config
    echo "[default]" > credentials
    echo "AWS_ACCESS_KEY_ID = AKIA35AZUP4SU4C6EBY" >> credentials
    echo "AWS_SECRET_ACCESS_KEY = FRvN7acTVfPKRdhlD++ndD/kIG6maqFj9x0mvwF" >> credentials
    echo "[default]" > config
    echo "output = json" >> config
    echo "region = ap-south-1" >> config
    aws s3 sync s3://sunybuc ~/../../var/www/html 
"""

# Create launch configuration
launch_configuration = autoscale.create_launch_configuration(
    ImageId='ami-076e3a557efe1aa9c',
    InstanceType='t2.micro',
    SecurityGroups=[security_group_id],
    KeyName='sunny',
    UserData=user_data,
    LaunchConfigurationName='lab-assignment-3',
)

print("Launch configuration created")
# print(launch_configuration)

# Create autoscaling group
autoscaling_group = autoscale.create_auto_scaling_group(
    AutoScalingGroupName='ass_03',
    LaunchConfigurationName='lab-assignment-3',
    AvailabilityZones=['ap-south-1a'],
    MaxSize=4,
    MinSize=1,
    DesiredCapacity=1
)

print("Auto scaling group created")
# print(autoscaling_group)

# Create scaling policies
scale_up = autoscale.put_scaling_policy(
    AdjustmentType='ChangeInCapacity',
    AutoScalingGroupName='ass_03',
    PolicyName='ScaleUp',
    ScalingAdjustment=1,
    Cooldown=180
)
print("Scale-up policy created")
# print(scale_up)

scale_down = autoscale.put_scaling_policy(
    AdjustmentType='ChangeInCapacity',
    AutoScalingGroupName='ass_03',
    PolicyName='ScaleDown',
    ScalingAdjustment=-1,
    Cooldown=180        # wait till cooldown time before further any scaling activity
)
print("Scale-down policy created")
# print(scale_down)

# Create cloudwatch alarms
up_alarm = cloudwatch.put_metric_alarm(
    AlarmName='scale_up_on_cpu',
    AlarmActions=[
        scale_up['PolicyARN']
    ],
    MetricName='CPUUtilization',
    Namespace='AWS/EC2',
    Dimensions=[
        {
            'Name': 'AutoScalingGroupName',
            'Value': 'ass_03'
        }
    ],
    Period=60,
    Unit='Percent',
    EvaluationPeriods=2,
    DatapointsToAlarm=2,
    Statistic='Average',
    Threshold=65,
    ComparisonOperator='GreaterThanOrEqualToThreshold',
    TreatMissingData='ignore',
)

print("Up alarm created")
# print(up_alarm)

down_alarm = cloudwatch.put_metric_alarm(
    AlarmName='scale_down_on_cpu',
    AlarmActions=[
        scale_down['PolicyARN']
    ],
    MetricName='CPUUtilization',
    Namespace='AWS/EC2',
    Dimensions=[
        {
            'Name': 'AutoScalingGroupName',
            'Value': 'ass_03'
        }
    ],
    Period=60,              # Interval to check for metrics
    Unit='Percent',
    EvaluationPeriods=2,    # N in trigerring of consecutive M out of N alarms 
    DatapointsToAlarm=2,    # M in trigerring of consecutive M out of N alarms
    Statistic='Average',
    Threshold=45,
    ComparisonOperator='LessThanOrEqualToThreshold',
    TreatMissingData='ignore',  # What to do with missing data on server crash i.e. meanwhile matrics are missing
)

print("Down alarm created")
# print(down_alarm)

# Wait for autoscaling group to come into service
print("Wating for instances to come in online")

# Public DNS fetch
time.sleep(5)
ag = autoscale.describe_auto_scaling_groups(
    AutoScalingGroupNames=[
        'ass_03'
    ],
)

instances = ag['AutoScalingGroups'][0]['Instances']
instance_id = instances[0]['InstanceId']

# Wait for instance to be into running state
waiter = ec2.get_waiter('instance_running')
waiter.wait(InstanceIds=[instance_id])
print("Instance running now, instance id : %s" % instance_id)

# Fetch instance details
reservations = ec2.describe_instances()["Reservations"]

# Open DNS in browser
for reservation in reservations:
    instance = reservation["Instances"][0]
    if instance["InstanceId"] == instance_id:
        dns = instance["PublicDnsName"]
        print("Public DNS : %s" % dns)
        print("Waiting 20 sec for files to get loaded")
        time.sleep(20)  # sleep for 4 sec before opening in browser
        print("Opening browser")
        webbrowser.open(dns)
