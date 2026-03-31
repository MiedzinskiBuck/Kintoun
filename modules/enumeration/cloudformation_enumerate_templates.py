MODULE_METADATA = {
    "name": "cloudformation_enumerate_templates",
    "display_name": "CloudFormation Enumerate Templates",
    "category": "enumeration",
    "description": "Enumerate CloudFormation stack templates in a selected region or across all regions.",
    "requires_region": False,
    "inputs": [
        {
            "name": "region",
            "type": "region",
            "required": False,
            "description": "Optional AWS region. Leave empty to enumerate all regions.",
        }
    ],
    "output_type": "json",
    "risk_level": "low",
}

from functions import Cloudformation_handler, region_parser, utils


def help():
    return


def collect_inputs():
    try:
        selected_region = input("Region (optional): ").strip()
    except RuntimeError:
        selected_region = ""
    return {"region": selected_region}


def parse_stack_summaries(response):
    items = []
    for stack in response.get("StackSummaries", []):
        items.append(
            {
                "stack_name": stack.get("StackName"),
                "stack_id": stack.get("StackId"),
                "status": stack.get("StackStatus"),
                "status_reason": stack.get("StackStatusReason"),
                "creation_time": str(stack.get("CreationTime")),
                "deletion_time": str(stack.get("DeletionTime")),
            }
        )
    return items


def main(botoconfig, session):
    inputs = collect_inputs()
    selected_region = inputs.get("region", "").strip()
    regions = [selected_region] if selected_region else region_parser.get_regions()

    results = {"regions": {}, "errors": []}
    total_templates = 0

    for region in regions:
        cfn = Cloudformation_handler.Cloudformation(botoconfig, session, region)
        response = cfn.list_stacks()
        if not response:
            results["regions"][region] = {"count": 0, "templates": [], "template_errors": []}
            results["errors"].append(
                {
                    "region": region,
                    "error": "Failed to list CloudFormation stacks in this region.",
                }
            )
            continue

        stack_summaries = parse_stack_summaries(response)
        while response.get("NextToken"):
            response = cfn.list_stacks(response.get("NextToken"))
            if not response:
                break
            stack_summaries.extend(parse_stack_summaries(response))

        templates = []
        template_errors = []
        for stack in stack_summaries:
            stack_id = stack.get("stack_id") or stack.get("stack_name")
            template_response = cfn.get_template(stack_id)
            if not template_response:
                template_errors.append(
                    {
                        "stack_id": stack.get("stack_id"),
                        "stack_name": stack.get("stack_name"),
                        "error": "Could not retrieve template for stack.",
                    }
                )
                continue

            templates.append(
                {
                    **stack,
                    "template_body": template_response.get("TemplateBody"),
                    "stages_available": template_response.get("StagesAvailable", []),
                }
            )

        results["regions"][region] = {
            "count": len(templates),
            "templates": templates,
            "template_errors": template_errors,
        }
        total_templates += len(templates)

    results["total_templates"] = total_templates
    return utils.module_result(data=results, errors=[])
