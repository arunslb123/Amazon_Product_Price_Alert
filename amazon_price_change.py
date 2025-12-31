#!/usr/bin/env python3
"""
Amazon Product Price Alert

Monitor Amazon product prices and receive notifications via SMS or email
when prices drop below your target.
"""

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from amazon_paapi import AmazonApi
from twilio.rest import Client as TwilioClient

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Configuration loaded from environment variables."""

    # Amazon API credentials
    amazon_access_key: str
    amazon_secret_key: str
    amazon_associate_tag: str
    amazon_region: str

    # Twilio credentials
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_from_number: str
    twilio_to_number: str

    # Email credentials
    gmail_user: str
    gmail_app_password: str
    email_from: str
    email_to: str

    # Product settings
    product_id: str
    expected_price: float

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            amazon_access_key=os.environ["AMAZON_ACCESS_KEY"],
            amazon_secret_key=os.environ["AMAZON_SECRET_KEY"],
            amazon_associate_tag=os.environ["AMAZON_ASSOCIATE_TAG"],
            amazon_region=os.getenv("AMAZON_REGION", "US"),
            twilio_account_sid=os.environ["TWILIO_ACCOUNT_SID"],
            twilio_auth_token=os.environ["TWILIO_AUTH_TOKEN"],
            twilio_from_number=os.environ["TWILIO_FROM_NUMBER"],
            twilio_to_number=os.environ["TWILIO_TO_NUMBER"],
            gmail_user=os.environ["GMAIL_USER"],
            gmail_app_password=os.environ["GMAIL_APP_PASSWORD"],
            email_from=os.environ["EMAIL_FROM"],
            email_to=os.environ["EMAIL_TO"],
            product_id=os.environ["AMAZON_PRODUCT_ID"],
            expected_price=float(os.environ["EXPECTED_PRICE"]),
        )


def send_sms(config: Config, message_body: str) -> Optional[str]:
    """
    Send an SMS notification using Twilio.

    Args:
        config: Application configuration
        message_body: The message content to send

    Returns:
        Message SID if successful, None otherwise
    """
    try:
        client = TwilioClient(config.twilio_account_sid, config.twilio_auth_token)
        message = client.messages.create(
            body=message_body,
            to=config.twilio_to_number,
            from_=config.twilio_from_number,
        )
        print(f"SMS sent successfully. SID: {message.sid}")
        return message.sid
    except Exception as e:
        print(f"Failed to send SMS: {e}")
        return None


def send_email(config: Config, title: str, price: float) -> bool:
    """
    Send an email notification using Gmail SMTP.

    Args:
        config: Application configuration
        title: Product title
        price: Current product price

    Returns:
        True if email sent successfully, False otherwise
    """
    subject = "Amazon Price Alert - Price Drop!"
    body = f"""
    Good news! The price has dropped on a product you're tracking.

    Product: {title}
    Current Price: ${price:.2f}
    Your Target Price: ${config.expected_price:.2f}

    This is a great time to make your purchase!
    """

    # Create message
    message = MIMEMultipart()
    message["From"] = config.email_from
    message["To"] = config.email_to
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    # Create secure SSL context
    context = ssl.create_default_context()

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(config.gmail_user, config.gmail_app_password)
            server.sendmail(config.email_from, config.email_to, message.as_string())
        print("Email sent successfully!")
        return True
    except smtplib.SMTPAuthenticationError:
        print("Failed to send email: Authentication error. Check your credentials.")
        return False
    except smtplib.SMTPException as e:
        print(f"Failed to send email: SMTP error - {e}")
        return False
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def get_product_info(config: Config) -> tuple[str, float]:
    """
    Fetch product information from Amazon.

    Args:
        config: Application configuration

    Returns:
        Tuple of (product_title, price)
    """
    amazon = AmazonApi(
        config.amazon_access_key,
        config.amazon_secret_key,
        config.amazon_associate_tag,
        config.amazon_region,
    )

    products = amazon.get_items(config.product_id)
    product = products[0]

    title = product.item_info.title.display_value
    price = float(product.offers.listings[0].price.amount)

    return title, price


def check_price_and_notify(config: Config) -> None:
    """
    Check product price and send notifications if below target.

    Args:
        config: Application configuration
    """
    print("Fetching product information...")
    title, price = get_product_info(config)

    print(f"Product: {title}")
    print(f"Current Price: ${price:.2f}")
    print(f"Target Price: ${config.expected_price:.2f}")

    if price <= config.expected_price:
        print("\nPrice is at or below target! Sending notifications...")
        notification_msg = f"Price Alert: {title} is now ${price:.2f}!"
        send_sms(config, notification_msg)
        send_email(config, title, price)
    else:
        print(f"\nPrice is still above target by ${price - config.expected_price:.2f}")


def main() -> None:
    """Main entry point for the price alert script."""
    try:
        config = Config.from_env()
        check_price_and_notify(config)
    except KeyError as e:
        print(f"Missing required environment variable: {e}")
        print("Please check your .env file or environment configuration.")
        raise SystemExit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
