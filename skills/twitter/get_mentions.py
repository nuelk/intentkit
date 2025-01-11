
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Type

from pydantic import BaseModel

from .base import Tweet, TwitterBaseTool


class TwitterGetMentionsInput(BaseModel):
    """Input schema for the TwitterGetMentions tool."""
    pass


class TwitterGetMentionsOutput(BaseModel):
    mentions: List[Tweet]
    error: Optional[str] = None


class TwitterGetMentions(TwitterBaseTool):
    """Tool for retrieving mentions from Twitter using the Twitter API v2.

    Attributes:
        name: The name of the tool.
        description: A description of the tool's purpose.
        args_schema: The schema for input arguments.
    """

    name: str = "twitter_get_mentions"
    description: str = "Retrieve tweets mentioning the authenticated user."
    args_schema: Type[BaseModel] = TwitterGetMentionsInput

    def _run(self) -> TwitterGetMentionsOutput:
        """Fetch mentions from Twitter.

        Returns:
            TwitterGetMentionsOutput: Contains the fetched mentions or an error message.
        """
        try:
            # Retrieve the last stored `since_id` for incremental fetching.
            last = self.store.get_agent_skill_data(self.agent_id, self.name, "last") or {}
            since_id = last.get("since_id")
            max_results = 100 if since_id else 10

            # Define the start time (mentions from the last 24 hours).
            start_time = (datetime.now(tz=timezone.utc) - timedelta(days=1)).isoformat(timespec="milliseconds")

            # Fetch mentions using the Twitter API client.
            response = self.client.get_users_mentions(
                id=self.client.get_me()[0].id,
                max_results=max_results,
                since_id=since_id,
                start_time=start_time,
                expansions=["referenced_tweets.id", "attachments.media_keys"],
                tweet_fields=["created_at", "author_id", "text", "referenced_tweets", "attachments"],
            )

            mentions = []
            if response.data:
                for tweet in response.data:
                    mention = Tweet(
                        id=str(tweet.id),
                        text=tweet.text,
                        author_id=str(tweet.author_id),
                        created_at=tweet.created_at,
                        referenced_tweets=getattr(tweet, "referenced_tweets", None),
                        attachments=getattr(tweet, "attachments", None),
                    )
                    mentions.append(mention)

            # Update `since_id` for future requests.
            if response.meta and "newest_id" in response.meta:
                last["since_id"] = response.meta["newest_id"]
                self.store.save_agent_skill_data(self.agent_id, self.name, "last", last)

            return TwitterGetMentionsOutput(mentions=mentions)

        except AttributeError as attr_err:
            return TwitterGetMentionsOutput(mentions=[], error=f"Attribute error: {str(attr_err)}")
        except KeyError as key_err:
            return TwitterGetMentionsOutput(mentions=[], error=f"Key error: {str(key_err)}")
        except Exception as e:
            return TwitterGetMentionsOutput(mentions=[], error=f"Unexpected error: {str(e)}")

    async def _arun(self) -> TwitterGetMentionsOutput:
        """Asynchronous version of the `_run` method.

        Note:
            This tool does not have a native async implementation, so the sync version is used.
        """
        return self._run()
