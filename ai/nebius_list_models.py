"""
You can use this script to list all available models from Nebius.
You can run it from the ../main.py file.
"""


def nebius_list_models(client):
    """List all available models from Nebius."""
    models = client.models.list()
    for model in models.data:
        print(f"Model ID: {model.id}")
