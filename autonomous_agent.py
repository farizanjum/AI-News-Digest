#!/usr/bin/env python3
"""
Autonomous News Digest Agent

This agent runs continuously and automatically sends daily news digests
to all subscribers at their preferred times.
"""

import os
import asyncio
import schedule
import time
import logging
from datetime import datetime, timedelta
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('autonomous_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AutonomousDigestAgent:
    def __init__(self):
        """Initialize the autonomous digest agent."""
        self.email_service = None
        self.news_service = None
        self.upsc_service = None
        self._initialize_services()
        
    def _initialize_services(self):
        """Initialize all required services."""
        try:
            from services.email_service import EmailService
            from services.news_service import NewsService
            from upsc_digest.upsc_digest import UPSCDigest
            
            self.email_service = EmailService()
            self.news_service = NewsService()
            self.upsc_service = UPSCDigest()
            
            logger.info("All services initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            raise
    
    async def send_tech_digests(self):
        """Send tech news digests to all tech subscribers."""
        logger.info("Starting tech digest distribution...")
        
        try:
            from database.database import SessionLocal
            from database.models import Subscriber
            
            db = SessionLocal()
            try:
                # Get all active tech subscribers
                tech_subscribers = db.query(Subscriber).filter(
                    Subscriber.is_active == True,
                    Subscriber.digest_type.in_(['tech', 'both'])
                ).all()
                
                logger.info(f"Found {len(tech_subscribers)} tech subscribers")
                
                if not tech_subscribers:
                    logger.info("No tech subscribers found")
                    return
                
                # Fetch tech articles once for all subscribers
                logger.info("Fetching tech articles...")
                articles = await self.news_service.fetch_tech_articles()
                logger.info(f"Fetched {len(articles)} tech articles")
                
                if not articles:
                    logger.warning("No tech articles found to send")
                    return
                
                # Send digest to each subscriber
                success_count = 0
                for subscriber in tech_subscribers:
                    try:
                        # Handle custom interests
                        if '|custom:' in subscriber.preferences:
                            base_prefs, custom_interests = subscriber.preferences.split('|custom:')
                            custom_articles = self.news_service.get_custom_curated_news(
                                base_prefs, custom_interests
                            )
                            if custom_articles:
                                articles_to_send = custom_articles
                                preferences = [custom_interests]
                            else:
                                articles_to_send = articles
                                preferences = base_prefs.split(',')
                        else:
                            articles_to_send = articles
                            preferences = subscriber.preferences.split(',')
                        
                        # Send the digest
                        success = await asyncio.to_thread(
                            self.email_service.send_tech_digest,
                            subscriber.email,
                            subscriber.name,
                            articles_to_send,
                            preferences
                        )
                        
                        if success:
                            success_count += 1
                            # Update last digest sent timestamp
                            subscriber.last_digest_sent = datetime.now()
                            db.commit()
                            logger.info(f"Tech digest sent to {subscriber.email}")
                        else:
                            logger.error(f"Failed to send tech digest to {subscriber.email}")
                        
                        # Small delay between sends
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error sending tech digest to {subscriber.email}: {e}")
                        continue
                
                logger.info(f"Tech digest distribution completed: {success_count}/{len(tech_subscribers)} successful")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in tech digest distribution: {e}")
    
    async def send_upsc_digests(self):
        """Send UPSC digests to all UPSC subscribers."""
        logger.info("Starting UPSC digest distribution...")
        
        try:
            from database.database import SessionLocal
            from database.models import Subscriber
            
            db = SessionLocal()
            try:
                # Get all active UPSC subscribers
                upsc_subscribers = db.query(Subscriber).filter(
                    Subscriber.is_active == True,
                    Subscriber.digest_type.in_(['upsc', 'both'])
                ).all()
                
                logger.info(f"Found {len(upsc_subscribers)} UPSC subscribers")
                
                if not upsc_subscribers:
                    logger.info("No UPSC subscribers found")
                    return
                
                # Fetch UPSC articles and generate digest
                logger.info("Fetching UPSC articles...")
                articles = self.upsc_service.fetch_news()
                logger.info(f"Fetched {len(articles)} UPSC articles")
                
                if not articles:
                    logger.warning("No UPSC articles found, generating empty digest")
                    digest_html = self.upsc_service.generate_empty_digest()
                else:
                    digest_html = self.upsc_service.generate_digest(articles)
                
                # Send digest to each subscriber
                success_count = 0
                for subscriber in upsc_subscribers:
                    try:
                        success = await asyncio.to_thread(
                            self.email_service.send_upsc_digest,
                            subscriber.email,
                            subscriber.name,
                            digest_html
                        )
                        
                        if success:
                            success_count += 1
                            # Update last digest sent timestamp
                            subscriber.last_digest_sent = datetime.now()
                            db.commit()
                            logger.info(f"UPSC digest sent to {subscriber.email}")
                        else:
                            logger.error(f"Failed to send UPSC digest to {subscriber.email}")
                        
                        # Small delay between sends
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error sending UPSC digest to {subscriber.email}: {e}")
                        continue
                
                logger.info(f"UPSC digest distribution completed: {success_count}/{len(upsc_subscribers)} successful")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in UPSC digest distribution: {e}")
    
    def run_tech_digest_job(self):
        """Wrapper for tech digest job to run in scheduler."""
        logger.info("Tech digest job triggered")
        asyncio.run(self.send_tech_digests())
    
    def run_upsc_digest_job(self):
        """Wrapper for UPSC digest job to run in scheduler."""
        logger.info("UPSC digest job triggered")
        asyncio.run(self.send_upsc_digests())
    
    def update_last_run_time(self, digest_type: str):
        """Update the last run time in the database."""
        try:
            from database.database import SessionLocal
            from database.models import DigestSchedule
            
            db = SessionLocal()
            try:
                schedule_record = db.query(DigestSchedule).filter(
                    DigestSchedule.digest_type == digest_type
                ).first()
                
                if schedule_record:
                    schedule_record.last_run = datetime.now()
                    # Calculate next run (next day at the same time)
                    current_time = datetime.now()
                    next_run = current_time.replace(
                        hour=int(schedule_record.scheduled_time.split(':')[0]),
                        minute=int(schedule_record.scheduled_time.split(':')[1]),
                        second=0,
                        microsecond=0
                    ) + timedelta(days=1)
                    schedule_record.next_run = next_run
                    db.commit()
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error updating last run time for {digest_type}: {e}")
    
    def setup_schedules(self):
        """Setup the daily schedules for digest distribution."""
        try:
            from database.database import SessionLocal
            from database.models import DigestSchedule
            
            db = SessionLocal()
            try:
                schedules = db.query(DigestSchedule).filter(
                    DigestSchedule.is_active == True
                ).all()
                
                for sched in schedules:
                    time_str = sched.scheduled_time
                    digest_type = sched.digest_type
                    
                    if digest_type == 'tech':
                        schedule.every().day.at(time_str).do(self.run_tech_digest_job)
                        logger.info(f"Scheduled tech digest for {time_str} daily")
                    elif digest_type == 'upsc':
                        schedule.every().day.at(time_str).do(self.run_upsc_digest_job)
                        logger.info(f"Scheduled UPSC digest for {time_str} daily")
                
                if not schedules:
                    # Set default schedules to 8:00 PM if none exist
                    logger.info("No schedules found, setting defaults to 8:00 PM...")
                    schedule.every().day.at("20:00").do(self.run_tech_digest_job)
                    schedule.every().day.at("20:00").do(self.run_upsc_digest_job)
                    logger.info("Default schedules set: Tech and UPSC at 20:00 (8:00 PM)")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error setting up schedules: {e}")
            # Fallback to 8:00 PM schedules
            schedule.every().day.at("20:00").do(self.run_tech_digest_job)
            schedule.every().day.at("20:00").do(self.run_upsc_digest_job)
            logger.info("Fallback schedules set to 8:00 PM")
    
    def run_continuously(self):
        """Run the agent continuously."""
        logger.info("Starting Autonomous News Digest Agent...")
        
        # Setup the database and schedules
        try:
            from database.database import create_tables, init_database
            create_tables()
            init_database()
        except Exception as e:
            logger.error(f"Error setting up database: {e}")
        
        # Setup schedules
        self.setup_schedules()
        
        logger.info("Agent is now running. Press Ctrl+C to stop.")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Agent stopped by user")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            raise
    
    def send_test_digests(self):
        """Send test digests immediately (for testing purposes)."""
        logger.info("Sending test digests...")
        
        async def run_tests():
            await self.send_tech_digests()
            await self.send_upsc_digests()
        
        asyncio.run(run_tests())
        logger.info("Test digests completed")


def main():
    """Main entry point for the autonomous agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Autonomous News Digest Agent')
    parser.add_argument('--test', action='store_true', 
                       help='Send test digests immediately instead of running continuously')
    parser.add_argument('--tech-only', action='store_true',
                       help='Send only tech digests (for testing)')
    parser.add_argument('--upsc-only', action='store_true', 
                       help='Send only UPSC digests (for testing)')
    
    args = parser.parse_args()
    
    agent = AutonomousDigestAgent()
    
    if args.test:
        if args.tech_only:
            asyncio.run(agent.send_tech_digests())
        elif args.upsc_only:
            asyncio.run(agent.send_upsc_digests())
        else:
            agent.send_test_digests()
    else:
        agent.run_continuously()


if __name__ == "__main__":
    main() 