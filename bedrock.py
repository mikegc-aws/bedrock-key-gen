import boto3

class Bedrock:
    def __init__(self, region="us-east-1"):
        self.bedrock = boto3.client(service_name="bedrock", region_name=region)
        self.region = region

    def foundation_models(self):
        try:
            response = self.bedrock.list_foundation_models(
                byInferenceType='ON_DEMAND'
            )
            model_list = []
            for model in response.get('modelSummaries', []):
                model_list.append({
                    'label': model.get('modelName', ''),
                    'value': model.get('modelArn', ''),
                    'groupName': model.get('providerName', '')
                })
            return model_list
        except botocore.exceptions.EndpointConnectionError:
            print(f"\nSorry, Bedrock is not available in the {self.region} region.")
            return None
        except Exception as e:
            print(f"\nAn error occurred while fetching Bedrock models: {str(e)}")
            return None