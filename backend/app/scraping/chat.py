#!/usr/bin/env python3
"""
Simple CLI chat script to talk to the LLM using the project's LLM client.
Loads environment variables from the local .env file.
"""

import os
import sys
from dotenv import load_dotenv

# Ensure we can import from the current directory even if run from elsewhere
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from llm_client import build_default_llm_client, LLMMessage

def main():
    # Load environment variables from backend/app/scraping/.env
    env_path = os.path.join(current_dir, ".env")
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)
    else:
        # Fallback to general environment
        load_dotenv()

    print("=" * 60)
    print("      LLM Chat Client (using OpenRouterClient)")
    print("=" * 60)

    try:
        # Build client using existing factory function
        client = build_default_llm_client()
        print(f"Model:     {client.model}")
        print(f"Referer:   {client.http_referer}")
        print(f"App Title: {client.app_title}")
        print("-" * 60)
    except Exception as e:
        print(f"Error initializing LLM Client: {e}")
        print("Please check your .env file in backend/app/scraping/.env")
        sys.exit(1)

    print("Type your message and press Enter.")
    print("Commands: '/clear' to clear history, '/exit' or '/quit' to exit.")
    print("-" * 60)

    # Maintain conversation history
    history: list[LLMMessage] = []

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Goodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("/exit", "/quit"):
            print("Goodbye!")
            break

        if user_input.lower() == "/clear":
            history.clear()
            print("Chat history cleared!")
            continue

        # Add user message to history
        history.append(LLMMessage(role="user", content=user_input))

        print("LLM is thinking...", end="\r")

        try:
            response = client.chat(history)
            # Add LLM response to history for conversation memory
            history.append(LLMMessage(role="assistant", content=response.content))
            
            # Clear "thinking..." line and print response
            sys.stdout.write("\033[K")  # Clear line
            print(f"\nLLM: {response.content}")
        except Exception as e:
            sys.stdout.write("\033[K")  # Clear line
            print(f"\nError: {e}")
            # Remove last user message since response failed
            if history:
                history.pop()

if __name__ == "__main__":
    main()
