import boto3

class Regions:
    def __init__(self):
        return self.list()

    @staticmethod
    def list():
        ec2 = boto3.client('ec2')
        response = ec2.describe_regions()
        regions = [
            {
                'label': region['RegionName'],
                'value': region['RegionName']
            }
            for region in response['Regions']
        ]
        # Sort the regions list based on the 'label' key
        return sorted(regions, key=lambda x: x['label'])
