def nebius_list_models(client):
    """List all available models from Nebius."""
    models = client.models.list()
    for model in models.data:
        print(f"Model ID: {model.id}")


# if __name__ == "__main__":
#     # List available models
#     nebius_list_models()
