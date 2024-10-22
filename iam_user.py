import boto3, json
from iam_policy import IAMPolicy

class IAMUser:
    def __init__(self, username, create_user_if_required=False):
        self.username = username
        self.iam_client = boto3.client('iam')
        self.sts_client = boto3.client('sts')
        self.account_id = self.sts_client.get_caller_identity()["Account"]
        self.user = self._get_user()
        self.policies = []
        
        if self.user is None and create_user_if_required:
            self.create()
        
        if self.user:
            self._load_policies()

    def _get_user(self):
        try:
            response = self.iam_client.get_user(UserName=self.username)
            return response['User']
        except self.iam_client.exceptions.NoSuchEntityException:
            return None

    def _load_policies(self):
        try:
            response = self.iam_client.list_attached_user_policies(UserName=self.username)
            for policy in response['AttachedPolicies']:
                self.policies.append(IAMPolicy(policy['PolicyName']))
        except Exception as e:
            print(f"Error loading policies for user {self.username}: {str(e)}")

    def create(self):
        if self.user is None:
            try:
                response = self.iam_client.create_user(UserName=self.username)
                self.user = response['User']
                print(f"User {self.username} created successfully.")
            except Exception as e:
                print(f"Error creating user {self.username}: {str(e)}")
        else:
            print(f"User {self.username} already exists.")

    def read(self):
        if self.user:
            return self.user
        else:
            print(f"User {self.username} does not exist.")
            return None

    def update(self, new_path=None, new_username=None):
        if self.user:
            try:
                update_params = {}
                if new_path:
                    update_params['NewPath'] = new_path
                if new_username:
                    update_params['NewUserName'] = new_username

                response = self.iam_client.update_user(UserName=self.username, **update_params)
                self.user = self._get_user()  # Refresh user info
                print(f"User {self.username} updated successfully.")
                if new_username:
                    self.username = new_username
            except Exception as e:
                print(f"Error updating user {self.username}: {str(e)}")
        else:
            print(f"User {self.username} does not exist.")

    def delete(self):
        if self.user:
            try:
                # First, detach all policies
                for policy in self.policies:
                    self.remove_policy(policy.policy_name)
                
                self.iam_client.delete_user(UserName=self.username)
                self.user = None
                self.policies = []
                print(f"User {self.username} deleted successfully.")
            except Exception as e:
                print(f"Error deleting user {self.username}: {str(e)}")
        else:
            print(f"User {self.username} does not exist.")

    def add_policy(self, policy_name, policy_document=None):
        if self.user:
            policy = IAMPolicy(policy_name, policy_document)
            if not policy.policy:
                # Create the policy if it doesn't exist
                if policy_document:
                    policy.create(policy_document)
                else:
                    print(f"Policy {policy_name} does not exist and no policy document provided to create it.")
                    return
            
            if policy.policy:
                try:
                    self.iam_client.attach_user_policy(
                        UserName=self.username,
                        PolicyArn=policy.policy['Arn']
                    )
                    self.policies.append(policy)
                    print(f"Policy {policy_name} attached to user {self.username} successfully.")
                except Exception as e:
                    print(f"Error attaching policy {policy_name} to user {self.username}: {str(e)}")
        else:
            print(f"User {self.username} does not exist.")

    def remove_policy(self, policy_name):
        try:
            policy_arn = f"arn:aws:iam::{self.account_id}:policy/{policy_name}"
            self.iam_client.detach_user_policy(
                UserName=self.username,
                PolicyArn=policy_arn
            )
            print(f"Policy {policy_name} detached from user {self.username}")
            self.policies = [p for p in self.policies if p.policy_name != policy_name]
            return True
        except Exception as e:
            print(f"Error detaching policy {policy_name} from user {self.username}: {str(e)}")
            return False

    def list_policies(self):
        return [policy.policy_name for policy in self.policies]
    
    def get_policies(self):
        return self.policies
    
    def delete_all_policies(self):
        policies_to_delete = self.policies.copy()
        all_deleted = True
        for policy in policies_to_delete:
            try:
                if self.remove_policy(policy.policy_name):
                    if policy.delete():
                        print(f"Policy {policy.policy_name} deleted successfully.")
                    else:
                        print(f"Failed to delete policy {policy.policy_name}")
                        all_deleted = False
                else:
                    all_deleted = False
            except Exception as e:
                print(f"Error processing policy {policy.policy_name}: {str(e)}")
                all_deleted = False
        
        remaining_policies = self.get_policies()
        if remaining_policies:
            print(f"Warning: {len(remaining_policies)} policies could not be deleted.")
            for policy in remaining_policies:
                print(f"- {policy.policy_name}")
        
        if all_deleted:
            print("All policies have been successfully deleted.")
        else:
            print("Some policies could not be deleted. Please check the warnings above.")

    def access_keys(self, rotate=False):
        # Get the AWS Systems Manager client
        ssm_client = boto3.client('ssm')
        parameter_name = f"/iam_user/{self.username}/access_keys"

        try:
            # Try to retrieve existing access keys from Parameter Store
            response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
            access_keys = json.loads(response['Parameter']['Value'])

            if rotate:

                # Deactivate the existing access key
                self.iam_client.update_access_key(
                    UserName=self.username,
                    AccessKeyId=access_keys['AccessKeyId'],
                    Status='Inactive'
                )
                print(f"Existing access key {access_keys['AccessKeyId']} deactivated for user {self.username}")

                # Delete the existing access key
                self.iam_client.delete_access_key(
                    UserName=self.username,
                    AccessKeyId=access_keys['AccessKeyId']
                )
                print(f"Existing access key {access_keys['AccessKeyId']} deleted for user {self.username}")

                # Create new access key
                new_key = self.iam_client.create_access_key(UserName=self.username)['AccessKey']
                
                # Update Parameter Store with new access key
                new_access_keys = {
                    'AccessKeyId': new_key['AccessKeyId'],
                    'SecretAccessKey': new_key['SecretAccessKey']
                }
                ssm_client.put_parameter(
                    Name=parameter_name,
                    Value=json.dumps(new_access_keys),
                    Type='SecureString',
                    Overwrite=True
                )

                print(f"Access keys rotated for user {self.username}")
                return new_access_keys
            else:
                return access_keys

        except ssm_client.exceptions.ParameterNotFound:
            # If no access keys exist, create new ones
            new_key = self.iam_client.create_access_key(UserName=self.username)['AccessKey']
            
            # Store new access keys in Parameter Store
            new_access_keys = {
                'AccessKeyId': new_key['AccessKeyId'],
                'SecretAccessKey': new_key['SecretAccessKey']
            }
            ssm_client.put_parameter(
                Name=parameter_name,
                Value=json.dumps(new_access_keys),
                Type='SecureString'
            )

            print(f"New access keys created for user {self.username}")
            return new_access_keys

        except Exception as e:
            print(f"Error managing access keys for user {self.username}: {str(e)}")
            return None
