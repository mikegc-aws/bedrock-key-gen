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
    # Get the IAM user for the session (bedrock-developer-<session_user>)
    session_user = get_session_user()
    bedrock_developer_user = IAMUser(f"bedrock-developer-{session_user}", create_user_if_required=True)
    
    ###########################################################################

    # Get the list of regions
    regions = Regions.list()
    region_menu = TreeMenu(regions, include_all=False, title="AWS Regions", question="Select a region:", single_select=True)
    selected_region = region_menu.run()
    
    if not selected_region:
        print("No region selected. Exiting.")
        return

    ###########################################################################

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

    ###########################################################################


    # Initialize Bedrock with the selected region
    bedrock = Bedrock(region=selected_region[0])

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

    #########################################################

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


if __name__ == "__main__":
    main()
