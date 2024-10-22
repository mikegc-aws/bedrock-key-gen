import boto3
from iam_policy import IAMPolicy

class IAMUser:
    def __init__(self, username, create_user_if_required=False):
        self.username = username
        self.iam_client = boto3.client('iam')
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
        if self.user:
            policy = next((p for p in self.policies if p.policy_name == policy_name), None)
            if policy:
                try:
                    self.iam_client.detach_user_policy(
                        UserName=self.username,
                        PolicyArn=policy.policy['Arn']
                    )
                    self.policies.remove(policy)
                    print(f"Policy {policy_name} detached from user {self.username} successfully.")
                except Exception as e:
                    print(f"Error detaching policy {policy_name} from user {self.username}: {str(e)}")
            else:
                print(f"Policy {policy_name} is not attached to user {self.username}.")
        else:
            print(f"User {self.username} does not exist.")

    def list_policies(self):
        return [policy.policy_name for policy in self.policies]
