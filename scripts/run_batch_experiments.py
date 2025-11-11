#!/usr/bin/env python3
"""
Batch Experiment Runner for RRI Orchestrator

This script allows you to run multiple experiments automatically without the GUI.
Perfect for systematic testing, A/B comparisons, and reproducibility studies.

Usage:
    python run_batch_experiments.py prompts.txt --provider-a gemini --provider-b openai
    python run_batch_experiments.py prompts.txt --flip  # Run again with flipped order
    python run_batch_experiments.py prompts.json --config experiment_config.json
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import our modules
from core import database
from config import model_config
from clients.gemini import GoogleGeminiClient
from clients.openai import OpenAIClient

# Load environment variables
load_dotenv()


class BatchExperimentRunner:
    """Runs multiple experiments automatically from a list of prompts."""
    
    def __init__(
        self,
        provider_a: str,
        provider_b: str,
        model_a_variant: str,
        model_b_variant: str,
        max_turns: int = 5,
        flip: bool = False,
        verbose: bool = True,
        dry_run: bool = False
    ):
        """
        Initialize batch runner.
        
        Args:
            provider_a: First provider ("gemini" or "openai")
            provider_b: Second provider ("gemini" or "openai")
            model_a_variant: Model variant for provider A
            model_b_variant: Model variant for provider B
            max_turns: Maximum conversation turns per experiment
            flip: If True, swap A and B for second run
            verbose: Print progress messages
            dry_run: If True, don't create experiments in database
        """
        self.provider_a = provider_a
        self.provider_b = provider_b
        self.model_a_variant = model_a_variant
        self.model_b_variant = model_b_variant
        self.max_turns = max_turns
        self.flip = flip
        self.verbose = verbose
        self.dry_run = dry_run
        
        # Initialize clients
        self.client_a = self._get_client(provider_a, model_a_variant)
        self.client_b = self._get_client(provider_b, model_b_variant)
        
        if not self.client_a or not self.client_b:
            raise ValueError("Failed to initialize LLM clients. Check API keys.")
        
        self.results = []
    
    def _get_client(self, provider: str, model_variant: str):
        """Get LLM client instance."""
        if provider == "gemini":
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                print(f"ERROR: GOOGLE_API_KEY not found in .env")
                return None
            model_id = model_config.get_model_id("gemini", model_variant)
            return GoogleGeminiClient(api_key=api_key, model_id=model_id)
        
        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print(f"ERROR: OPENAI_API_KEY not found in .env")
                return None
            model_id = model_config.get_model_id("openai", model_variant)
            return OpenAIClient(api_key=api_key, model_id=model_id)
        
        return None
    
    def run_single_experiment(
        self,
        prompt: str,
        experiment_name: Optional[str] = None
    ) -> Dict:
        """
        Run a single experiment with the given prompt.
        
        Args:
            prompt: Initial prompt/topic for the conversation
            experiment_name: Optional name for the experiment
            
        Returns:
            Dict with experiment results and metadata
        """
        # Generate experiment name
        if not experiment_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            experiment_name = f"Batch_{timestamp}"
        
        # Create system prompts
        model_a_display = model_config.get_model_display_name(self.provider_a, self.model_a_variant)
        model_b_display = model_config.get_model_display_name(self.provider_b, self.model_b_variant)
        
        prompt_a = (
            f"You are {model_a_display}. You are having a conversation with {model_b_display}. "
            f"Keep your responses brief and concise (2-3 sentences). Engage in a thoughtful discussion."
        )
        prompt_b = (
            f"You are {model_b_display}. You are having a conversation with {model_a_display}. "
            f"Keep your responses brief and concise (2-3 sentences). Engage in a thoughtful discussion."
        )
        
        if self.verbose:
            print(f"\n{'='*70}")
            print(f"Experiment: {experiment_name}")
            print(f"Models: {model_a_display} ↔ {model_b_display}")
            print(f"Initial prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
            print(f"{'='*70}")
        
        # Dry run - just print what would happen
        if self.dry_run:
            if self.verbose:
                print(f"[DRY RUN] Would create experiment with {self.max_turns} turns")
                print(f"[DRY RUN] Provider A: {self.provider_a} ({self.model_a_variant})")
                print(f"[DRY RUN] Provider B: {self.provider_b} ({self.model_b_variant})")
            return {
                "experiment_id": None,
                "experiment_name": experiment_name,
                "status": "dry_run",
                "turns": 0,
                "dry_run": True
            }
        
        # Create experiment in database
        exp_id = database.create_experiment(
            model_config.PROVIDERS[self.provider_a],
            model_config.PROVIDERS[self.provider_b],
            prompt_a,
            prompt_b,
            self.max_turns,
            model_a_variant=self.model_a_variant,
            model_b_variant=self.model_b_variant,
            name=experiment_name
        )
        
        if self.verbose:
            print(f"\n{'='*70}")
            print(f"Experiment #{exp_id}: {experiment_name}")
            print(f"Models: {model_a_display} ↔ {model_b_display}")
            print(f"Initial prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
            print(f"{'='*70}")
        
        # Initialize conversation histories
        model_a_history = [{"role": "system", "content": prompt_a}]
        model_b_history = [{"role": "system", "content": prompt_b}]
        
        # Add initial user prompt
        if prompt:
            database.log_message(exp_id, "researcher", prompt)
            model_a_history.append({"role": "user", "content": prompt})
            model_b_history.append({"role": "user", "content": prompt})
        
        # Run conversation turns
        messages = []
        for turn in range(1, self.max_turns + 1):
            if self.verbose:
                print(f"\n--- Turn {turn}/{self.max_turns} ---")
            
            try:
                # Model A responds
                if self.verbose:
                    print(f"🤖 {model_a_display} thinking...")
                
                response_a = self.client_a.generate_response(model_a_history)
                database.log_message(exp_id, model_config.PROVIDERS[self.provider_a], response_a)
                messages.append({"speaker": model_a_display, "content": response_a, "turn": turn})
                
                # Update histories
                model_a_history.append({"role": "assistant", "content": response_a})
                model_b_history.append({"role": "user", "content": response_a})
                
                if self.verbose:
                    print(f"   └─ {response_a[:150]}{'...' if len(response_a) > 150 else ''}")
                
                # Model B responds
                if self.verbose:
                    print(f"🤖 {model_b_display} thinking...")
                
                response_b = self.client_b.generate_response(model_b_history)
                database.log_message(exp_id, model_config.PROVIDERS[self.provider_b], response_b)
                messages.append({"speaker": model_b_display, "content": response_b, "turn": turn})
                
                # Update histories
                model_b_history.append({"role": "assistant", "content": response_b})
                model_a_history.append({"role": "user", "content": response_b})
                
                if self.verbose:
                    print(f"   └─ {response_b[:150]}{'...' if len(response_b) > 150 else ''}")
                
            except Exception as e:
                error_msg = f"Error in turn {turn}: {str(e)}"
                print(f"❌ {error_msg}")
                
                # Determine error type
                error_type = "api_error"
                if "rate" in str(e).lower() or "quota" in str(e).lower() or "limit" in str(e).lower():
                    error_type = "rate_limit"
                elif "timeout" in str(e).lower() or "connection" in str(e).lower():
                    error_type = "network_error"
                
                # Log error to database
                database.log_message(exp_id, "system", error_msg, is_error=True, error_type=error_type)
                database.update_experiment_status(exp_id, "error")
                
                break
        
        result = {
            "experiment_id": exp_id,
            "experiment_name": experiment_name,
            "initial_prompt": prompt,
            "model_a": f"{self.provider_a}/{self.model_a_variant}",
            "model_b": f"{self.provider_b}/{self.model_b_variant}",
            "turns_completed": turn,
            "messages": messages
        }
        
        if self.verbose:
            print(f"\n✅ Experiment #{exp_id} completed: {turn} turns")
        
        return result
    
    def run_batch(self, prompts: List[str], experiment_prefix: str = "Batch") -> List[Dict]:
        """
        Run multiple experiments from a list of prompts.
        
        Args:
            prompts: List of prompts to use
            experiment_prefix: Prefix for experiment names
            
        Returns:
            List of experiment results
        """
        print(f"\n{'='*70}")
        print(f"BATCH EXPERIMENT RUN")
        print(f"Total experiments: {len(prompts)}")
        print(f"Model A: {self.provider_a}/{self.model_a_variant}")
        print(f"Model B: {self.provider_b}/{self.model_b_variant}")
        print(f"Max turns per experiment: {self.max_turns}")
        print(f"{'='*70}")
        
        results = []
        for i, prompt in enumerate(prompts, 1):
            exp_name = f"{experiment_prefix}_{i:02d}"
            
            try:
                result = self.run_single_experiment(prompt, exp_name)
                results.append(result)
            except Exception as e:
                print(f"ERROR in experiment {i}: {e}")
                results.append({
                    "experiment_name": exp_name,
                    "error": str(e),
                    "initial_prompt": prompt
                })
        
        self.results = results
        return results
    
    def run_batch_with_flip(
        self,
        prompts: List[str],
        experiment_prefix: str = "Batch"
    ) -> Dict[str, List[Dict]]:
        """
        Run experiments twice: once with A→B, then with B→A (flipped).
        
        Args:
            prompts: List of prompts
            experiment_prefix: Prefix for experiment names
            
        Returns:
            Dict with "original" and "flipped" results
        """
        print("\n" + "="*70)
        print("BATCH WITH FLIP MODE")
        print("="*70)
        
        # Run original order
        print("\n🔵 PHASE 1: Original order")
        original_results = self.run_batch(prompts, f"{experiment_prefix}_Original")
        
        # Flip providers and models
        print("\n🔴 PHASE 2: Flipped order")
        self.provider_a, self.provider_b = self.provider_b, self.provider_a
        self.model_a_variant, self.model_b_variant = self.model_b_variant, self.model_a_variant
        self.client_a, self.client_b = self.client_b, self.client_a
        
        flipped_results = self.run_batch(prompts, f"{experiment_prefix}_Flipped")
        
        return {
            "original": original_results,
            "flipped": flipped_results
        }
    
    def save_results_summary(self, output_file: str = "batch_results_summary.json"):
        """Save batch results summary to JSON file."""
        output_path = Path(output_file)
        with output_path.open("w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📊 Results saved to: {output_path.absolute()}")


def load_prompts_from_file(filepath: str) -> List[str]:
    """
    Load prompts from a text or JSON file.
    
    Text format: One prompt per line
    JSON format: Array of strings or objects with "prompt" key
    """
    path = Path(filepath)
    
    if not path.exists():
        raise FileNotFoundError(f"Prompts file not found: {filepath}")
    
    if path.suffix == ".json":
        with path.open() as f:
            data = json.load(f)
        
        # Handle different JSON formats
        if isinstance(data, list):
            if all(isinstance(item, str) for item in data):
                return data
            elif all(isinstance(item, dict) for item in data):
                return [item.get("prompt", item.get("text", "")) for item in data]
        
        raise ValueError("Invalid JSON format. Expected array of strings or objects with 'prompt' key.")
    
    else:  # Assume text file
        with path.open() as f:
            prompts = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        return prompts


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run batch experiments for RRI Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic run with 15 prompts
  python run_batch_experiments.py prompts.txt --provider-a gemini --provider-b openai
  
  # Specify exact models
  python run_batch_experiments.py prompts.txt \\
    --provider-a gemini --model-a gemini-2.5-pro \\
    --provider-b openai --model-b gpt-4o
  
  # Run with flip (30 total experiments)
  python run_batch_experiments.py prompts.txt --flip \\
    --provider-a gemini --provider-b openai --turns 10
  
  # Use JSON config file
  python run_batch_experiments.py prompts.json --config config.json
        """
    )
    
    parser.add_argument("prompts_file", help="Path to file containing prompts (txt or json)")
    parser.add_argument("--provider-a", default="gemini", choices=["gemini", "openai"],
                        help="First LLM provider (default: gemini)")
    parser.add_argument("--provider-b", default="openai", choices=["gemini", "openai"],
                        help="Second LLM provider (default: openai)")
    parser.add_argument("--model-a", dest="model_a_variant",
                        help="Model variant for provider A (e.g., gemini-2.5-pro, gpt-4o)")
    parser.add_argument("--model-b", dest="model_b_variant",
                        help="Model variant for provider B")
    parser.add_argument("--turns", "--max-turns", type=int, default=5,
                        help="Maximum turns per experiment (default: 5)")
    parser.add_argument("--flip", action="store_true",
                        help="Run experiments twice: original and flipped order")
    parser.add_argument("--prefix", default="Batch",
                        help="Prefix for experiment names (default: Batch)")
    parser.add_argument("--output", default="batch_results_summary.json",
                        help="Output file for results summary")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress progress messages")
    parser.add_argument("--dry-run", action="store_true",
                        help="Test run without creating experiments in database")
    parser.add_argument("--config", help="JSON config file with all settings")
    
    args = parser.parse_args()
    
    # Load config from file if provided
    if args.config:
        with open(args.config) as f:
            config = json.load(f)
        
        args.provider_a = config.get("provider_a", args.provider_a)
        args.provider_b = config.get("provider_b", args.provider_b)
        args.model_a_variant = config.get("model_a_variant", args.model_a_variant)
        args.model_b_variant = config.get("model_b_variant", args.model_b_variant)
        args.turns = config.get("max_turns", args.turns)
        args.flip = config.get("flip", args.flip)
    
    # Set default model variants if not specified
    if not args.model_a_variant:
        args.model_a_variant = "gemini-2.5-pro" if args.provider_a == "gemini" else "gpt-4o-mini"
    
    if not args.model_b_variant:
        args.model_b_variant = "gpt-4o-mini" if args.provider_b == "openai" else "gemini-2.5-pro"
    
    # Ensure database is set up
    database.setup_database()
    
    # Load prompts
    try:
        prompts = load_prompts_from_file(args.prompts_file)
        print(f"✅ Loaded {len(prompts)} prompts from {args.prompts_file}")
    except Exception as e:
        print(f"ERROR loading prompts: {e}")
        sys.exit(1)
    
    # Initialize runner
    try:
        runner = BatchExperimentRunner(
            provider_a=args.provider_a,
            provider_b=args.provider_b,
            model_a_variant=args.model_a_variant,
            model_b_variant=args.model_b_variant,
            max_turns=args.turns,
            flip=args.flip,
            verbose=not args.quiet,
            dry_run=args.dry_run
        )
    except Exception as e:
        print(f"ERROR initializing runner: {e}")
        sys.exit(1)
    
    # Show configuration
    if not args.quiet:
        print(f"\n{'='*70}")
        print(f"BATCH EXPERIMENT CONFIGURATION")
        print(f"{'='*70}")
        print(f"Provider A: {args.provider_a} ({args.model_a_variant})")
        print(f"Provider B: {args.provider_b} ({args.model_b_variant})")
        print(f"Max turns: {args.turns}")
        print(f"Flip mode: {'Yes' if args.flip else 'No'}")
        print(f"Dry run: {'Yes' if args.dry_run else 'No'}")
        print(f"Total prompts: {len(prompts)}")
        if args.flip:
            print(f"Total experiments: {len(prompts) * 2} (with flip)")
        else:
            print(f"Total experiments: {len(prompts)}")
        print(f"{'='*70}")
        
        if args.dry_run:
            print("\n⚠️  DRY RUN MODE - No experiments will be created in database")
    
    # Run experiments
    try:
        if args.flip:
            results = runner.run_batch_with_flip(prompts, args.prefix)
            if not args.dry_run:
                print(f"\n{'='*70}")
                print(f"✅ COMPLETED: {len(prompts) * 2} total experiments")
                print(f"   - Original order: {len(results['original'])} experiments")
                print(f"   - Flipped order: {len(results['flipped'])} experiments")
                print(f"{'='*70}")
        else:
            results = runner.run_batch(prompts, args.prefix)
            if not args.dry_run:
                print(f"\n{'='*70}")
                print(f"✅ COMPLETED: {len(results)} experiments")
                print(f"{'='*70}")
        
        # Save summary
        runner.save_results_summary(args.output)
        
        print("\n📊 View results:")
        print(f"   - In GUI: Navigate to 'View History' tab in the web app")
        print(f"   - In database: sqlite3 rri_lab.db")
        print(f"   - Export: Use GUI or database queries")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR during batch run: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
