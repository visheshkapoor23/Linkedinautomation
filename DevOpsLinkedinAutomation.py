import openai
import schedule
import time
import os
import logging
import requests
from dotenv import load_dotenv
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EKS
from diagrams.azure.compute import AKS
from diagrams.onprem.client import User
from diagrams.onprem.compute import Server

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("linkedin_poster.log"), logging.StreamHandler()],
)

# LinkedIn API credentials
CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")  # Refresh this token periodically

# OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logging.error("OpenAI API key not found in environment variables.")
    exit(1)

# List of topics to cycle through weekly
TOPICS = [
    "DevOps",
    "Kubernetes",
    "Docker",
    "Helm",
    "Terraform",
    "Azure",
    "EKS",
    "AKS",
]

# SEO keywords for Google and LinkedIn
SEO_KEYWORDS = {
    "DevOps": "DevOps practices, CI/CD pipelines, automation, cloud-native development, infrastructure as code",
    "Kubernetes": "Kubernetes orchestration, container management, cloud-native apps, K8s clusters, microservices",
    "Docker": "Docker containers, containerization, Docker images, DevOps tools, cloud deployment",
    "Helm": "Helm charts, Kubernetes package manager, app deployment, Helm templates, DevOps tools",
    "Terraform": "Terraform infrastructure as code, cloud provisioning, multi-cloud deployment, DevOps automation",
    "Azure": "Microsoft Azure, cloud computing, Azure DevOps, cloud services, Azure Kubernetes Service (AKS)",
    "EKS": "Amazon EKS, Kubernetes on AWS, managed Kubernetes, cloud-native apps, AWS services",
    "AKS": "Azure Kubernetes Service, managed Kubernetes, cloud-native apps, Azure DevOps, container orchestration",
}

# Track the current topic index
current_topic_index = 0

def generate_content(topic):
    """Generate SEO-friendly content for the given topic using OpenAI."""
    try:
        prompt = f"""
        Write a short LinkedIn post about {topic} in the context of DevOps and cloud-native technologies.
        The post should be engaging, informative, and suitable for a professional audience.
        Include relevant keywords for Google and LinkedIn SEO: {SEO_KEYWORDS[topic]}.
        """
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=200,
            n=1,
            stop=None,
            temperature=0.7,
        )
        return response.choices[0].text.strip()
    except Exception as e:
        logging.error(f"Failed to generate content for {topic}: {e}")
        return None

def generate_diagram(topic):
    """Generate a diagram for the given topic."""
    try:
        diagram_path = f"diagrams/{topic}_diagram.png"
        with Diagram(topic, filename=diagram_path, outformat="png", show=False):
            if topic == "Kubernetes":
                with Cluster("Kubernetes Cluster"):
                    master = Server("Master Node")
                    worker1 = Server("Worker Node 1")
                    worker2 = Server("Worker Node 2")
                    master >> Edge(color="blue") >> worker1
                    master >> Edge(color="blue") >> worker2
            elif topic == "Docker":
                with Cluster("Docker Containers"):
                    container1 = Server("Container 1")
                    container2 = Server("Container 2")
                    container1 >> Edge(color="green") >> container2
            elif topic == "EKS":
                EKS("Amazon EKS") >> Edge(color="orange") >> Server("Worker Nodes")
            elif topic == "AKS":
                AKS("Azure AKS") >> Edge(color="purple") >> Server("Worker Nodes")
            elif topic == "Terraform":
                User("Developer") >> Edge(color="red") >> Server("Terraform")
                Server("Terraform") >> Edge(color="red") >> [Server("AWS"), Server("Azure"), Server("GCP")]
            elif topic == "Helm":
                User("Developer") >> Edge(color="yellow") >> Server("Helm")
                Server("Helm") >> Edge(color="yellow") >> Server("Kubernetes")
            elif topic == "Azure":
                User("Developer") >> Edge(color="blue") >> Server("Azure Services")
                Server("Azure Services") >> Edge(color="blue") >> [Server("AKS"), Server("Functions"), Server("Storage")]
            elif topic == "DevOps":
                User("Developer") >> Edge(color="black") >> Server("CI/CD Pipeline")
                Server("CI/CD Pipeline") >> Edge(color="black") >> [Server("Kubernetes"), Server("Docker"), Server("Terraform")]
        return diagram_path
    except Exception as e:
        logging.error(f"Failed to generate diagram for {topic}: {e}")
        return None

def upload_image_to_linkedin(image_path):
    """Upload an image to LinkedIn and return the asset URN."""
    try:
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
        }
        register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
        register_data = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": "urn:li:person:{YOUR_PERSON_URN}",  # Replace with your LinkedIn Person URN
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent",
                    }
                ],
            }
        }
        response = requests.post(register_url, headers=headers, json=register_data)
        response.raise_for_status()
        upload_url = response.json()["value"]["uploadMechanism"][
            "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
        ]["uploadUrl"]
        asset_urn = response.json()["value"]["asset"]

        # Upload the image
        with open(image_path, "rb") as image_file:
            upload_response = requests.post(upload_url, headers=headers, files={"file": image_file})
        upload_response.raise_for_status()

        return asset_urn
    except Exception as e:
        logging.error(f"Failed to upload image to LinkedIn: {e}")
        return None

def post_to_linkedin(content, image_urn):
    """Post content with an image to LinkedIn."""
    try:
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
        post_url = "https://api.linkedin.com/v2/ugcPosts"
        post_data = {
            "author": "urn:li:person:{YOUR_PERSON_URN}",  # Replace with your LinkedIn Person URN
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "IMAGE",
                    "media": [{"status": "READY", "media": image_urn}],
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        response = requests.post(post_url, headers=headers, json=post_data)
        response.raise_for_status()
        logging.info("Posted to LinkedIn successfully!")
    except Exception as e:
        logging.error(f"Failed to post to LinkedIn: {e}")

def post_to_linkedin_with_image():
    """Generate content and diagram for the current topic and post it to LinkedIn."""
    global current_topic_index

    topic = TOPICS[current_topic_index]
    logging.info(f"Generating content and diagram for topic: {topic}")

    content = generate_content(topic)
    if not content:
        logging.error("No content generated. Skipping post.")
        return

    diagram_path = generate_diagram(topic)
    if not diagram_path:
        logging.error("No diagram generated. Skipping post.")
        return

    logging.info(f"Generated Content for {topic}:\n{content}")
    logging.info(f"Diagram saved at: {diagram_path}")

    image_urn = upload_image_to_linkedin(diagram_path)
    if not image_urn:
        logging.error("Failed to upload image. Skipping post.")
        return

    post_to_linkedin(content, image_urn)

    # Move to the next topic for the next week
    current_topic_index = (current_topic_index + 1) % len(TOPICS)
    logging.info(f"Next topic: {TOPICS[current_topic_index]}")

# Schedule the post every day at 6 PM
#schedule.every().day.at("18:00").do(post_to_linkedin_with_image)

# Keep the script running
logging.info("LinkedIn poster started. Waiting for scheduled posts...")
while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Script stopped by user.")
        break
    except Exception as e:
        logging.error(f"Unexpected error in scheduler: {e}")