import boto3

class IAMPolicy:
    def __init__(self, policy_name, policy_document=None, description=None):
        self.policy_name = policy_name
        self.iam_client = boto3.client('iam')
        self.policy = self._get_policy()
        
        if self.policy is None and policy_document:
            self.create(policy_document, description)

    def _get_policy(self):
        try:
            response = self.iam_client.get_policy(PolicyArn=f"arn:aws:iam::aws:policy/{self.policy_name}")
            return response['Policy']
        except self.iam_client.exceptions.NoSuchEntityException:
            return None

    def create(self, policy_document, description=None):
        if self.policy is None:
            try:
                params = {
                    'PolicyName': self.policy_name,
                    'PolicyDocument': policy_document
                }
                if description:
                    params['Description'] = description

                print(f"Creating policy {self.policy_name} with document: {policy_document}")

                response = self.iam_client.create_policy(**params)
                self.policy = response['Policy']
                print(f"Policy {self.policy_name} created successfully.")
            except Exception as e:
                print(f"Error creating policy {self.policy_name}: {str(e)}")
        else:
            print(f"Policy {self.policy_name} already exists.")

    def read(self):
        if self.policy:
            return self.policy
        else:
            print(f"Policy {self.policy_name} does not exist.")
            return None

    def update(self, policy_document):
        if self.policy:
            try:
                response = self.iam_client.create_policy_version(
                    PolicyArn=self.policy['Arn'],
                    PolicyDocument=policy_document,
                    SetAsDefault=True
                )
                self.policy = self._get_policy()  # Refresh policy info
                print(f"Policy {self.policy_name} updated successfully.")
            except Exception as e:
                print(f"Error updating policy {self.policy_name}: {str(e)}")
        else:
            print(f"Policy {self.policy_name} does not exist.")

    def delete(self):
        if self.policy:
            try:
                # Delete all non-default versions first
                versions = self.iam_client.list_policy_versions(PolicyArn=self.policy['Arn'])['Versions']
                for version in versions:
                    if not version['IsDefaultVersion']:
                        self.iam_client.delete_policy_version(
                            PolicyArn=self.policy['Arn'],
                            VersionId=version['VersionId']
                        )
                
                # Now delete the policy
                self.iam_client.delete_policy(PolicyArn=self.policy['Arn'])
                self.policy = None
                print(f"Policy {self.policy_name} deleted successfully.")
            except Exception as e:
                print(f"Error deleting policy {self.policy_name}: {str(e)}")
        else:
            print(f"Policy {self.policy_name} does not exist.")
