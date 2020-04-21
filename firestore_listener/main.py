from firestore_counter_config import PROJECT_NAME, TOPIC
from google.cloud import pubsub_v1

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_NAME, TOPIC)


def on_delete_author(data, context):
    resource = context.resource.split("/authors/")[1]
    on_delete(resource, "author")


def on_delete_document(data, context):
    resource = context.resource.split("/documents/")[1]
    on_delete(resource, "document")


def on_delete(data, type):
    publish(data, type, "delete")


def on_create_author(data, context):
    resource = context.resource.split("/authors/")[1]
    on_create(resource, "author")


def on_create_document(data, context):
    resource = context.resource.split("/documents/")[1]
    on_create(resource, "document")


def on_create(data, type):
    publish(data, type, "create")


def publish(data, type, action):
    data = data.encode("utf-8")
    publisher.publish(topic_path, data=data, type=type, action=action).result()
