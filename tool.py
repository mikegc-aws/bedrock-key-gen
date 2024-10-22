import boto3
import json
import secrets
import string
from iam_user import IAMUser
from iam_policy import IAMPolicy
from regions import Regions
from bedrock import Bedrock
from tree_menu import TreeMenu
from datetime import datetime, timedelta, timezone

def get_session_user():
    try:
        sts_client = boto3.client('sts')
        response = sts_client.get_caller_identity()
        
        # Extract the user or role name from the ARN
        arn = response['Arn']
        name = arn.split('/')[-1]
        
        return name
    except Exception as e:
        print(f"Error getting session user: {str(e)}")
        return None

def main():
    print("Bedrock Developer Tool")
    print("Checking session user...")
    session_user = get_session_user()
    print(f"Session user: {session_user}")
    print("Getting IAM user...")
    bedrock_developer_user = IAMUser(f"bedrock-developer-{session_user}", create_user_if_required=True)

    menu_options = [
        "Create access policy for Bedrock model access",
        "List access policies for Bedrock model access",
        "Rotate access keys",
        "DELETE ALL POLICIES NOW",
        "Exit"
    ]
    menu = TreeMenu(
        [{"label": option, "value": option} for option in menu_options],
        include_all=False,
        title="Bedrock Developer Tool",
        question="Select an option:",
        single_select=True
    )
    selected_option = menu.run()[0]

    if selected_option == "Create access policy for Bedrock model access":
        create_access_policy(bedrock_developer_user, session_user)
    elif selected_option == "List access policies for Bedrock model access":
        list_access_policies(bedrock_developer_user)
    elif selected_option == "Rotate access keys":
        rotate_access_keys(bedrock_developer_user)
    elif selected_option == "DELETE ALL POLICIES NOW":
        delete_all_policies(bedrock_developer_user)
    elif selected_option == "Exit":
        print("Exiting the application. Goodbye!")

def create_access_policy(bedrock_developer_user, session_user):
    # Get the list of regions
    regions = Regions.list()
    region_menu = TreeMenu(regions, include_all=False, title="AWS Regions", question="Select a region:", single_select=True)
    selected_region = region_menu.run()[0]
    
    if not selected_region:
        print("No region selected. Exiting.")
        return

    duration_options = [
        {'label': '1 hour', 'value': 1*60*60},
        {'label': '6 hours', 'value': 6*60*60},
        {'label': '12 hours', 'value': 12*60*60},
        {'label': '24 hours', 'value': 24*60*60}
    ]

    duration_menu = TreeMenu(duration_options, include_all=False, title="Session Duration", question="Select the duration for the temporary credentials:", single_select=True)
    selected_duration = duration_menu.run()

    if not selected_duration:
        print("No duration selected. Exiting.")
        return

    duration_seconds = selected_duration[0]

    # Initialize Bedrock with the selected region
    bedrock = Bedrock(region=selected_region)

    # Select Bedrock models
    foundation_models = bedrock.foundation_models()
    if foundation_models is None:
        print("Exiting due to Bedrock unavailability.")
        return

    model_menu = TreeMenu(
        foundation_models,
        include_all=True,
        title=f"Region: {selected_region[0]}",
        question="Select one or more foundation models:"
    )
    selected_models = model_menu.run()
    
    print(f"\nSelected region: {selected_region[0]}")
    print(f"Selected model ARNs:\n-",  '\n- '.join(selected_models))

    # Use datetime.now() with UTC timezone
    current_time = datetime.now(timezone.utc)
    expiration_time = current_time + timedelta(seconds=duration_seconds)

    policy_document = json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": "bedrock:InvokeModel",
            "Resource": selected_models,
            "Condition": {
                "DateLessThan": {
                    "aws:CurrentTime": expiration_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                }
            }
        }]
    })

    # Generate a short random string (e.g., 8 characters)
    random_suffix = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))

    bedrock_developer_user.add_policy(
        f"bedrock-dev-{session_user}-{random_suffix}",
        policy_document=policy_document
    )

    # Get access keys for the user
    access_keys = bedrock_developer_user.access_keys()
    display_access_keys(access_keys)

def display_access_keys(access_keys):
    if access_keys:
        print("\nAccess Keys:")
        print("For Windows CMD:")
        print(f"set AWS_ACCESS_KEY_ID={access_keys['AccessKeyId']}")
        print(f"set AWS_SECRET_ACCESS_KEY={access_keys['SecretAccessKey']}")
        print("\nFor Windows PowerShell:")
        print(f"$env:AWS_ACCESS_KEY_ID='{access_keys['AccessKeyId']}'")
        print(f"$env:AWS_SECRET_ACCESS_KEY='{access_keys['SecretAccessKey']}'")
        print("\nFor macOS/Linux:")
        print(f"export AWS_ACCESS_KEY_ID={access_keys['AccessKeyId']}")
        print(f"export AWS_SECRET_ACCESS_KEY={access_keys['SecretAccessKey']}")
        print("\nYou can copy and paste these commands into your terminal to set the environment variables.")
    else:
        print("\nNo access keys found or there was an error retrieving them.")

def list_access_policies(bedrock_developer_user):
    policies = bedrock_developer_user.get_policies()
    print("\nBedrock Access Policies:")
    for p in policies:
        policy = IAMPolicy(p.policy_name)
        print(policy.summary())

def rotate_access_keys(bedrock_developer_user):
    confirm = input("Are you sure you want to rotate access keys? (y/n): ")
    if confirm.lower() == 'y':
        access_keys = bedrock_developer_user.access_keys(rotate=True)
        display_access_keys(access_keys)
    else:
        print("Access key rotation cancelled.")

def delete_all_policies(bedrock_developer_user):
    confirm = input("Are you sure you want to DELETE ALL POLICIES? This action cannot be undone. (y/n): ")
    if confirm.lower() == 'y':
        bedrock_developer_user.delete_all_policies()
        print("All policies have been deleted.")
    else:
        print("Policy deletion cancelled.")

if __name__ == "__main__":
    main()
