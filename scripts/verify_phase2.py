"""
Quick verification script for Phase 2 database schema.
Creates test robots with different AI providers to verify the new fields work.
"""

import asyncio
from src.database.models import User, RobotProfile, Experiment
from src.database.session import init_database, close_database


async def verify_phase2():
    """
    Verify Phase 2 database schema is working correctly.
    """
    print("=" * 60)
    print("Phase 2 Database Verification")
    print("=" * 60)
    
    await init_database()
    
    try:
        # Create test user
        user = await User.create(
            username='verification_user',
            email='verify@example.com',
            hashed_password='password123'
        )
        print("\n✓ Test user created")
        
        # Create GPT-4o robot
        robot_gpt = await RobotProfile.create(
            name='GPT-4o Verification Bot',
            description='OpenAI GPT-4o for testing',
            system_prompt='You are a helpful technical assistant.',
            ai_provider='openai',
            model_name='gpt-4o',
            default_temperature=0.3,
            created_by=user
        )
        print(f"\n✓ OpenAI Robot Created:")
        print(f"  Name: {robot_gpt.name}")
        print(f"  Provider: {robot_gpt.ai_provider}")
        print(f"  Model: {robot_gpt.model_name}")
        print(f"  Temperature: {robot_gpt.default_temperature}")
        
        # Create Gemini robot
        robot_gemini = await RobotProfile.create(
            name='Gemini Verification Bot',
            description='Google Gemini 2.0 Flash for testing',
            system_prompt='You are a creative assistant.',
            ai_provider='gemini',
            model_name='gemini-2.0-flash',
            default_temperature=0.9,
            created_by=user
        )
        print(f"\n✓ Gemini Robot Created:")
        print(f"  Name: {robot_gemini.name}")
        print(f"  Provider: {robot_gemini.ai_provider}")
        print(f"  Model: {robot_gemini.model_name}")
        print(f"  Temperature: {robot_gemini.default_temperature}")
        
        # Create experiment with both robots
        experiment = await Experiment.create(
            name='Multi-Provider Verification',
            description='Testing OpenAI vs Gemini',
            created_by=user,
            robot_a_profile=robot_gpt,
            robot_b_profile=robot_gemini
        )
        
        await experiment.fetch_related('robot_a_profile', 'robot_b_profile')
        
        print(f"\n✓ Experiment Created:")
        print(f"  Name: {experiment.name}")
        print(f"  Robot A: {experiment.robot_a_profile.name} ({experiment.robot_a_profile.ai_provider})")
        print(f"  Robot B: {experiment.robot_b_profile.name} ({experiment.robot_b_profile.ai_provider})")
        
        # Cleanup
        print("\n" + "=" * 60)
        print("Cleaning up test data...")
        await experiment.delete()
        await robot_gpt.delete()
        await robot_gemini.delete()
        await user.delete()
        
        print("=" * 60)
        print("✓ VERIFICATION SUCCESSFUL!")
        print("=" * 60)
        print("\nPhase 2 database schema is working correctly!")
        print("You can now:")
        print("  1. View robots in Adminer: http://localhost:8081")
        print("  2. Proceed with AI service implementation")
        
    except Exception as e:
        print(f"\n✗ VERIFICATION FAILED: {e}")
        raise
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(verify_phase2())
