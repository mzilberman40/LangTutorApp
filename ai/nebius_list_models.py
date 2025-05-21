def nebius_list_models(client):
    """List all available models from Nebius."""
    models = client.models.list()
    for model in models.data:
        print(f"Model ID: {model.id}")
