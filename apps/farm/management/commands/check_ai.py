"""Report the configured AI backend, and optionally run a live test prompt."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.farm import ai_advice, ai_openrouter


class Command(BaseCommand):
    help = "Check the AI provider configuration. Use --live to send a test prompt."

    def add_arguments(self, parser):
        parser.add_argument(
            "--live",
            action="store_true",
            help="Send a small prompt to the provider to verify the key and model.",
        )

    def handle(self, *args, **options):
        provider = getattr(settings, "AI_PROVIDER", "gemini")
        if provider == "openrouter":
            module, label, ask = ai_openrouter, "OpenRouter", ai_openrouter.ask_openrouter
            key_name = "OPENROUTER_API_KEY"
        else:
            module, label, ask = ai_advice, "Gemini", ai_advice.ask_gemini
            key_name = "GEMINI_API_KEY"

        configured = module.is_configured()
        self.stdout.write(f"Provider:  {label}")
        self.stdout.write(f"Model:     {module.model_name()}")
        self.stdout.write(f"API key:   {'set' if configured else 'not set'} ({key_name})")

        if not configured:
            self.stdout.write(
                self.style.WARNING(
                    f"Set {key_name} in .env (see .env.example) or the environment, then retry."
                )
            )
            return

        if not options["live"]:
            self.stdout.write(
                self.style.SUCCESS("Configuration looks OK. Run with --live to test the API.")
            )
            return

        self.stdout.write("Sending test prompt...")
        result = ask("Reply with exactly: OK")
        if not result.get("ok"):
            raise CommandError(result.get("error", "The AI provider rejected the request."))
        self.stdout.write(self.style.SUCCESS(f"Live check passed: {result['text'][:100]}"))
