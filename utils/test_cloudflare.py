import os
from dotenv import load_dotenv
from cloudflare import Cloudflare

load_dotenv()

CF_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CF_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CF_LIST_ID = os.getenv("CLOUDFLARE_LIST_ID", "")

client = Cloudflare(
    api_token=CF_API_TOKEN,
)


def get_lists():
    page = client.rules.lists.list(
        account_id=CF_ACCOUNT_ID,
    )
    for list in page:
        print(list["id"], list["name"])


def get_list():
    list = client.rules.lists.get(
        list_id=CF_LIST_ID,
        account_id=CF_ACCOUNT_ID,
    )
    print(list.name)


def get_list_content():
    page = client.rules.lists.items.list(account_id=CF_ACCOUNT_ID, list_id=CF_LIST_ID, per_page=10)

    for item in page:
        print(item["ip"])
    list = client.rules.lists.get(
        list_id=CF_LIST_ID,
        account_id=CF_ACCOUNT_ID,
    )
    print("Totel items in list:",  list.num_items)


# get_lists()
#get_list_content()
get_list()
