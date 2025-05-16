import os
from confluent_kafka import Producer, Consumer, KafkaException
from confluent_kafka import SerializingProducer, Consumer, KafkaException, TopicPartition, OFFSET_BEGINNING, KafkaError
from confluent_kafka.admin import (AdminClient, NewTopic, ConfigResource, 
                                   AclBindingFilter, ResourceType, ResourcePatternType,
                                   AclOperation, AclPermissionType)

import threading, json
from datetime import datetime, timezone
import time
import uuid

# Import settings and logging at the top level
from magicflow.libs.logging_service import LoggingService
from magicflow.config.config import settings

# Initialize logger at module level
logger = LoggingService().getLogger('__name__')

logger.debug(f"ENV variables: {(settings.as_dict())}")

bootstrap_servers = settings.bootstrap_servers
group_id = settings.group_id

sasl_conf = {
    'bootstrap.servers': settings.bootstrap_servers,
    'sasl.mechanism': settings.sasl_mechanism,
    'ssl.ca.location': settings.ssl_ca_location,
    'security.protocol': settings.security_protocol,
    'request.timeout.ms': settings.request_timeout_ms,
    'sasl.username': settings.sasl_username,
    'sasl.password': settings.sasl_password,
    'log.queue': 'false',
    'sasl.kerberos.principal': settings.sasl_username,
    'sasl.kerberos.keytab': '',
    'session.timeout.ms': settings.session_timeout_ms,
    'auto.offset.reset': settings.auto_offset_reset,
    'heartbeat.interval.ms': settings.heartbeat_interval_ms,
    'enable.auto.commit': False,
    'auto.commit.interval.ms': settings.auto_commit_interval_ms,
    'retries': settings.kafka_retries,
    'retry.backoff.ms': settings.retry_backoff_ms,
}

sasl_produc_conf = {
    'bootstrap.servers': settings.bootstrap_servers,
    'sasl.mechanism': settings.sasl_mechanism,
    'ssl.ca.location': settings.ssl_ca_location,
    'security.protocol': settings.security_protocol,
    'request.timeout.ms': settings.request_timeout_ms,
    'sasl.username': settings.sasl_username,
    'sasl.password': settings.sasl_password,
    'log.queue': 'false',
    'sasl.kerberos.principal': settings.sasl_username,
    'sasl.kerberos.keytab': '',
    'retries': settings.kafka_retries,
    'retry.backoff.ms': settings.retry_backoff_ms,
}

def generate_random_id():
    return str(uuid.uuid4())

def generate_formatted_date():
    current_datetime = datetime.now(timezone.utc)
    formatted_date = current_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
    return formatted_date

class KafkaConnect:
    def __init__(self):
        self.logger = logger
        # Add debug logging for SSL configuration
        logger.debug(f"Checking SSL CA location: {sasl_produc_conf['ssl.ca.location']}")
        if not os.path.exists(sasl_produc_conf['ssl.ca.location']):
            logger.error(f"SSL CA file not found at: {sasl_produc_conf['ssl.ca.location']}")
            raise FileNotFoundError(f"SSL CA certificate not found at {sasl_produc_conf['ssl.ca.location']}")
            
        try:
            admin_client = AdminClient(sasl_produc_conf)
            self.admin_client = admin_client
            self._create_required_topics()
        except Exception as e:
            logger.error(f"Failed to create admin client: {str(e)}")
            raise

    def _create_required_topics(self):
        """Create required Kafka topics if they don't exist."""
        required_topics = [
            settings.get("kafka_consume_queue_topic"),
            settings.get("kafka_report_queue_topic")
        ]

        for topic in required_topics:
            try:
                # Check if topic exists
                topic_metadata = self.admin_client.list_topics(timeout=10)
                if topic not in topic_metadata.topics:
                    logger.info(f"Creating topic: {topic}")
                    new_topic = NewTopic(
                        topic,
                        num_partitions=settings.get("kafka_num_partitions", 1),
                        replication_factor=settings.get("kafka_replication_factor", 1)
                    )
                    
                    # Set topic configurations if specified
                    configs = {}
                    if settings.get("kafka_retention_ms"):
                        configs["retention.ms"] = str(settings.kafka_retention_ms)
                    if settings.get("kafka_cleanup_policy"):
                        configs["cleanup.policy"] = settings.kafka_cleanup_policy
                    
                    if configs:
                        new_topic.set_config(configs)
                    
                    # Create the topic
                    fs = self.admin_client.create_topics([new_topic])
                    for topic_name, f in fs.items():
                        try:
                            f.result()  # Wait for topic creation to complete
                            logger.info(f"Successfully created topic: {topic_name}")
                        except Exception as e:
                            logger.error(f"Failed to create topic {topic_name}: {str(e)}")
                else:
                    logger.debug(f"Topic already exists: {topic}")
            except Exception as e:
                logger.error(f"Error checking/creating topic {topic}: {str(e)}")
                raise

    def kafka_produce(self, p_topic, message):
        try:
            producer = SerializingProducer(sasl_produc_conf)
            self.logger.info(f"Producing message to topic {p_topic}: {message}")
            
            try:
                result = producer.produce(
                    topic=p_topic,
                    value=str(message).encode('utf-8'),
                    partition=0,
                    on_delivery=lambda err, msg: self.delivery_report(err, msg)
                )
                producer.poll(0)
                producer.flush(timeout=5)
                
                self.logger.info(f"Message successfully produced to topic {p_topic}")
                return message
                
            except KafkaException as e:
                self.logger.error(f"Failed to produce to topic {p_topic}: {e}")
                return 0
                
        except KafkaException as e:
            if e.args[0].code() == KafkaError._AUTHORIZATION_ERROR:
                self.logger.error(f"Authentication failed: {e}")
            return 0
        
    def create_kafka_topic(self, topic):
        new_topic = NewTopic(topic, num_partitions=1, replication_factor=1)
        fs = self.admin_client.create_topics([new_topic])
        for topic, f in fs.items():
            try:
                f.result()  # The result itself is None
                logger.debug(f"KAFKA-SASL: Topic {topic} created")
                return 1
            except Exception as e:
                logger.warning(f"KAFKA-SASL: Failed to create topic {topic}: {e}")
                return 0

    def delivery_report(self, err, msg):
        if err is not None:
            self.logger.error(f"KAFKA-SASL: Message delivery failed: {err}")
        else:
            self.logger.info(f"KAFKA-SASL: Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

    def kafka_consume(self, c_topic, message_callback):
        consumer = None
        try:
            # Add group.id to the consumer configuration
            consumer_conf = sasl_conf.copy()
            consumer_conf['group.id'] = group_id
            consumer_conf['auto.offset.reset'] = 'earliest'  # Start reading from the beginning
            consumer_conf['enable.auto.commit'] = True  # Enable auto commit
            
            self.logger.info(f"Starting consumer with config: {consumer_conf}")
            consumer = Consumer(consumer_conf)
            
            self.logger.info(f"Subscribing to topic: {c_topic}")
            consumer.subscribe([c_topic])
            self.logger.debug(f"KAFKA-SASL: Consuming records from topic {c_topic}.")
            
            while True:
                msg = consumer.poll(timeout=1.0)
                if msg is None:
                    self.logger.debug("No message received in this poll")
                    continue
                    
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        self.logger.debug("Reached end of partition")
                        continue
                    else:
                        self.logger.error(f"KAFKA-SASL: Consumer error: {msg.error()}")
                        break
                
                try:
                    message_value = msg.value().decode('utf-8')
                    self.logger.info(f"KAFKA-SASL: Received message chunk: {message_value}")
                    self.logger.debug(f"KAFKA-SASL: Message chunk details - topic: {msg.topic()}, partition: {msg.partition()}, offset: {msg.offset()}")
                    
                    # Call the message callback directly with the message chunk
                    message_callback(msg.topic(), message_value)
                        
                except Exception as e:
                    self.logger.error(f"KAFKA-SASL: Error processing message chunk: {str(e)}")
                    continue
                
        except KeyboardInterrupt:
            self.logger.info("KAFKA-SASL: Consumer interrupted by user")
        except Exception as e:
            self.logger.error(f"KAFKA-SASL: Error in consumer: {str(e)}")
            raise
        finally:
            if consumer:
                consumer.close()
                self.logger.debug("KAFKA-SASL: Consumer closed")


def on_message_received(topic, message):
    logger.info(f'Received message on topic {topic}: {message}')


# return json message
def get_event_message(transaction_id, tenant, source="", type="", author="", message="", data={}, parent_id="", parent_type=""):
    # Clean up the data object to remove any non-serializable fields
    if isinstance(data, dict):
        # Remove managedFields if present as it's usually very large and not needed
        if 'history' in data:
            del data['history']
        
        # Remove last-applied-configuration if present
        if ('metadata' in data and 'annotations' in data['metadata'] and 
            'kubectl.kubernetes.io/last-applied-configuration' in data['metadata']['annotations']):
            del data['metadata']['annotations']['kubectl.kubernetes.io/last-applied-configuration']

    event_message = {
        "id": generate_random_id(),
        "parentId": parent_id,
        "parentType": parent_type,
        "transactionId": transaction_id,
        "tenant": tenant,
        "attributes": {
            "source": source,
            "type": type,
            "date": generate_formatted_date(),
            "author": author
        },
        "message": message,
        "data": data
    }
    
    try:
        # Ensure the entire message is JSON serializable
        return json.dumps(event_message)
    except TypeError as e:
        logger.warning(f"Failed to serialize event message, stripping data field: {e}")
        # Fallback: return message without data if serialization fails
        event_message["data"] = {}
        return json.dumps(event_message)

"""
{
  "id": "f7261fd8-4498-4185-962a-85bd5ec6e6f7",
  "parentId": "",
  "parentType": "system", 
  "transactionId": "dca56a55-6a15-4529-a3b3-566ca5722919",
  "tenant": "sview",
  "attributes": {
    "source": "sview-controller/pkg/api.(*Routes)PutApplicationAccessRequest()",
    "type": "cto2b.accessRequest.created",
    "date": "2024-01-29T11:24:58.763600",
    "author": "andriusb@cto2b.eu"
  },
  "message": "[demo] [andriusb@cto2b.eu] Created AccessRequest: [6e3598dd-8491-4a6b-be36-7241354314d3] app: [dev-demo-app-aws-rds-mysql-payments-gw1] for role [aws-rds-mysql-superuser]",
  "data": {}
}
"""