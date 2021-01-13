#! /usr/bin/env python3
import boto3


def find_latest_ami(search_string):
    ec2_client = boto3.client("ec2")
    response = ec2_client.describe_images(
        Filters=[
            {
                "Name": "name",
                "Values": [
                    search_string,
                ],
            },
        ]
    )
    try:
        ami_list = response["Images"]
        latest_ami = sorted(ami_list, key=lambda k: k["CreationDate"], reverse=True)[0]
    except:
        return None

    return latest_ami["ImageId"]


def lambda_handler(event, context):
    ec2 = boto3.client("ec2")
    response = ec2.describe_launch_templates(Filters=[{"Name": "tag-key", "Values": ["ami-search-string"]}])
    templates = response["LaunchTemplates"]
    if len(templates):
        print("Found {} launch templates".format(len(templates)))
    else:
        print("Found no launch templates with the 'ami-search-string' tag.")
        return "done"

    for template in templates:
        template_id = template["LaunchTemplateId"]
        name = template["LaunchTemplateName"]
        print("{}: ".format(name), end="")
        ami_id = None
        for t in template["Tags"]:
            if t["Key"] == "ami-search-string":
                ami_id = find_latest_ami(t["Value"])
                break  # leave loop if we found the correct key

        if not ami_id:
            print("Can't find an AMI with this search string. Exiting")
            return "error"

        # Get $Latest version of the template
        latest = ec2.describe_launch_template_versions(LaunchTemplateId=template_id, Versions=["$Latest"])
        data = latest["LaunchTemplateVersions"][0]["LaunchTemplateData"]

        # Replace ImageId with the new one
        if data["ImageId"] == ami_id:
            print("Already using the latest AMI.")
            continue
        else:
            print("Not using the latest AMI. Will create a new version")

        # Create new version
        response = ec2.create_launch_template_version(
            LaunchTemplateId=template_id, SourceVersion="$Latest", LaunchTemplateData={"ImageId": ami_id}
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
            print("Aborting due to an error while creating the new launch tempalte")
            print("The error was: {}".format(response))
            return "error"

    return "done"
