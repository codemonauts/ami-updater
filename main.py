#! /usr/bin/env python3

"""
Module to update all AWS EC2 Launch Templates to the newest AMI version.
"""

import boto3
from environs import Env

# Get config from environment
env = Env()
keep_amis = env.int("KEEP_AMIS", 3)


def find_latest_ami(search_string):
    """
    Returns the AMI ID of the latest AMI with the given search string
    """
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
    except Exception:  # pylint: disable=broad-exception-caught
        return None

    return latest_ami["ImageId"]


def lambda_handler(
    event, context
):  # pylint: disable=unused-argument,too-many-locals,too-many-branches,too-many-statements
    """
    Entrypoint for AWS Lambda
    """
    ec2 = boto3.client("ec2")
    response = ec2.describe_launch_templates(Filters=[{"Name": "tag-key", "Values": ["ami-search-string"]}])
    templates = response["LaunchTemplates"]
    if len(templates):
        print(f"Found {len(templates)} launch templates")
    else:
        print("Found no launch templates with the 'ami-search-string' tag.")
        return "done"

    for template in templates:
        template_id = template["LaunchTemplateId"]
        name = template["LaunchTemplateName"]
        print(f"{name}: ", end="")
        ami_id = None
        for tag in template["Tags"]:
            if tag["Key"] == "ami-search-string":
                ami_id = find_latest_ami(tag["Value"])
                break  # leave loop if we found the correct key

        if not ami_id:
            print("Can't find an AMI with this search string. Exiting")
            return "error"

        # Get $Latest version of the template
        latest = ec2.describe_launch_template_versions(LaunchTemplateId=template_id, Versions=["$Latest"])
        latest_version = latest["LaunchTemplateVersions"][0]["VersionNumber"]
        data = latest["LaunchTemplateVersions"][0]["LaunchTemplateData"]

        # Replace ImageId with the new one
        if data["ImageId"] == ami_id:
            print("Already using the latest AMI.")

        else:
            print("Not using the latest AMI. Will create a new version")

            # Create new version
            response = ec2.create_launch_template_version(
                LaunchTemplateId=template_id,
                SourceVersion="$Latest",
                LaunchTemplateData={"ImageId": ami_id},
            )

            # Update latest ID to the newly created version
            latest_version = response["LaunchTemplateVersion"]["VersionNumber"]

            if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
                print("Aborting due to an error while creating the new launch tempalte")
                print(f"The error was: {response}")
                return "error"

        # Update default version to latest version
        # Otherwise we couldn't delete old version if they are still set as default
        ec2.modify_launch_template(
            LaunchTemplateId=template_id,
            DefaultVersion=str(latest_version),
        )

        # we can't purge old versions if the counter is less then the limit
        if latest_version < keep_amis:
            return "done"

        # Cleanup of old template versions
        versions = ec2.describe_launch_template_versions(
            LaunchTemplateId=template_id, MaxVersion=str(latest_version - keep_amis)
        ).get("LaunchTemplateVersions", [])

        print(versions)

        for version in versions:
            ami_id = version["LaunchTemplateData"]["ImageId"]
            num = version["VersionNumber"]
            ami_details = ec2.describe_images(ImageIds=[ami_id])
            print(f"Deleting version {num} with attached AMI {ami_id} and snapshots")
            print(ami_details)
            # First: Deregister AMI
            try:
                ec2.deregister_image(ImageId=ami_id)
                print(f"Deregistered AMI {ami_id}")
            except Exception as ex:  # pylint: disable=broad-exception-caught
                print(f"Couldn't deregister AMI {ami_id}")
                print(f"Reason: {ex}")
            # Second: Delete corresponding version from launch template
            try:
                ec2.delete_launch_template_versions(
                    LaunchTemplateId=template_id,
                    Versions=[str(num)],
                )
                print(f"Removed version {num} from launch template {template_id}")
            except Exception as ex:  # pylint: disable=broad-exception-caught
                print(f"Couldn't remove version {num} from launch template {template_id}")
                print(f"Reason: {ex}")
            # Third: Delete all snapshots of the AMI
            try:
                block_devices = ami_details["Images"][0]["BlockDeviceMappings"]
                for block_device in block_devices:
                    snapshot_id = block_device["Ebs"]["SnapshotId"]
                    ec2.delete_snapshot(SnapshotId=snapshot_id, DryRun=False)
                    print(f"Deleted snapshot {snapshot_id} of AMI {ami_id}")
            except Exception as ex:  # pylint: disable=broad-exception-caught
                print(f"Couldn't delete snapshot {snapshot_id} of AMI {ami_id}")
                print(f"Reason: {ex}")

    return "done"
