from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Security

from jupychat.auth import verify_jwt
from jupychat.kernels import JupyChatKernelClient, get_nb_gpt_kernel_client
from jupychat.models import (
    CreateKernelRequest,
    CreatePageResponse,
    NewPageRequest,
    RunCellRequest,
    RunCellResponse,
)
from jupychat.suggestions import RUN_CELL_PARSE_FAIL
import requests
import json
import os

router = APIRouter(dependencies=[Security(verify_jwt)])


@router.post("/set-domain")
async def set_domain():
    """
    This endpoint instructs ChatGPT to ask the user for a domain name and checks if it's available.
    It returns a temporary subdomain and a site ID.
    """


@router.post("/create-page/{site_id}")
async def create_page(site_id: str, new_page_request: NewPageRequest) -> CreatePageResponse:
    """
    Create a page on your site.
    This endpoint instructs ChatGPT to ask the user for a topic, generate N pages, and execute the endpoint for each page.
    """

    page_id = create_wp_page(
        site_id=site_id,
        page_title=new_page_request.page_title,
        page_content=new_page_request.page_content,
    )
    return CreatePageResponse(page_id=page_id)


def get_site_credentials(site_id: str) -> Dict:
    """
    Return site credentials for given site_id

    TODO: store these in a database, this is still hardcoded for a single WP site ran locally
    """
    wp_api_base_url = ("http://localhost:8084/?rest_route=",)
    return {
        "wp_api_pages_url": f"{wp_api_base_url}/wp/v2/pages",
        "wp_username": os.environ["WP_USERNAME"],
        "wp_password": os.environ["WP_API_KEY"],
    }


def create_wp_page(site_id: str, page_title: str, page_content: Optional[str] = None) -> str:
    """
    Create a new page on a site for given site_id.
    Returns page_id.
    TODO: turn this into async def
    """
    wp_credentials = get_site_credentials(site_id)
    headers = {"Content-Type": "application/json"}
    new_page_data = {"title": page_title, "content": page_content, "status": "publish"}
    print(wp_credentials["wp_api_pages_url"])
    new_page_response = requests.post(
        wp_credentials["wp_api_pages_url"],
        auth=(wp_credentials["wp_username"], wp_credentials["wp_password"]),
        headers=headers,
        json=new_page_data,
    )
    new_page_response_data = json.loads(new_page_response.text)
    if "id" in new_page_response_data:
        return new_page_response_data["id"]

    raise HTTPException(status_code=400, detail="Unknown error occurred")
    # raise Exception(f"create_page: Er is een fout opgetreden: {new_page_response_data}")


@router.put("/update-page/{site_id}")
async def update_page():
    """
    This endpoint instructs ChatGPT to ask for the page to update and let the user review the content.
    After approval, it updates the page with the generated content.
    """


@router.post("/reserve-domain")
async def reserve_domain():
    """
    This endpoint reserves/buys the chosen domain name at the registrar on behalf of the user.
    The subdomain website will be transferred to the newly bought domain name.
    The user will receive an offer for a paid plan and must accept it by saying "I accept" and providing an email address.
    """


@router.post("/run-cell")
async def run_cell(
    request: RunCellRequest,
    kernel_client: JupyChatKernelClient = Depends(get_nb_gpt_kernel_client),
) -> RunCellResponse:
    """Execute a cell and return the result.

    The execution format is:

    ```json
    {
        "kernel_id": "<previously created kernel id>",
        "code": "print('hello world')"
    }
    ```
    """

    if not request.code:
        raise HTTPException(status_code=400, detail=RUN_CELL_PARSE_FAIL)

    if not request.kernel_id:
        request.kernel_id = (await kernel_client.start_kernel(CreateKernelRequest())).kernel_id

    try:
        return await kernel_client.run_cell(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing code: {e}")
