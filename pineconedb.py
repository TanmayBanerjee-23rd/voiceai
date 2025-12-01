from pinecone import Pinecone
import os

class PineconeDB:
    def __init__(self):
        self.api_key = os.getenv("PINECONE_API_KEY")
        if not self.api_key:
            raise ValueError("PINECONE_API_KEY environment variable is not set")
        self.pc = Pinecone(api_key=self.api_key)

    def has_index(self, index_name):
        return self.pc.has_index(index_name)

    def create_index_for_model(self,name, deletion_protection, tags, cloud, region, embed):
        self.pc.create_index_for_model(
            name=name,
            deletion_protection=deletion_protection,
            tags=tags,
            cloud=cloud,
            region=region,
            embed=embed
        )
    
    def get_client(self, index_name):
        if not self.has_index(index_name):
            self.create_index_for_model(
                name=index_name,
                deletion_protection="enabled",
                tags={
                    "environment": "development"
                },
                cloud="aws",
                region="us-east-1",
                embed={
                    "model":"llama-text-embed-v2",
                    "field_map":{"text": "chunk_text"}
                }
            )
        return self.pc.Index(index_name)