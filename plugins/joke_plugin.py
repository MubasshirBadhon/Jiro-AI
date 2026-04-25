"""Joke Plugin - Tell jokes to lighten the mood."""

from plugins.plugin_loader import PluginBase
import random

JOKES = [
    "Why don't scientists trust atoms? Because they make up everything!",
    "I told my wife she was drawing her eyebrows too high. She looked surprised.",
    "Why did the programmer quit his job? Because he didn't get arrays!",
    "What's a computer's least favorite food? Spam!",
    "Why do Java developers wear glasses? Because they can't C#!",
    "There are only 10 types of people: those who understand binary and those who don't.",
    "A SQL query walks into a bar, sees two tables and asks 'Can I join you?'",
    "Why was the JavaScript developer sad? Because he didn't Node how to Express himself!",
    "What's a programmer's favorite hangout place? Foo Bar!",
    "Why did the student eat his homework? Because his teacher told him it was a piece of cake!",
    "What do you call a student who got caught copying? A Ctrl+C student!",
    "Why was the math book sad? Because it had too many problems.",
    "What did the triangle say to the circle? You're pointless!",
    "Why couldn't the bicycle stand up by itself? It was two-tired!",
    "What do you call a fake noodle? An impasta!",
    "I'm reading a book about anti-gravity. It's impossible to put down!",
    "Did you hear about the mathematician who's afraid of negative numbers? He'll stop at nothing to avoid them!",
    "Why did the physics teacher break up with the biology teacher? There was no chemistry!",
]


class JokePlugin(PluginBase):
    name = "joke"
    description = "Tell jokes and lighten the mood"
    triggers = ["joke", "tell joke", "funny", "make me laugh", "humor",
                 "tell me a joke", "another joke"]

    async def execute(self, command: str, context: dict = None) -> str:
        return random.choice(JOKES)
