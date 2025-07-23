"""
Simple test to verify the project structure and imports.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.abspath('.'))

def test_imports():
    """Test that all modules can be imported without Google Cloud dependencies."""
    
    print("Testing configuration imports...")
    try:
        from config.settings import Settings
        settings = Settings()
        print(f"✓ Settings imported successfully, project_id: {settings.project_id}")
    except Exception as e:
        print(f"✗ Settings import failed: {e}")
    
    print("\nTesting agents structure...")
    try:
        # Test that agent files exist and have basic structure
        import agents
        print("✓ Agents package imported")
        
        # Check if agent files exist
        agent_files = ['triage_agent.py', 'solution_agent.py', 'action_agent.py']
        for agent_file in agent_files:
            agent_path = f'agents/{agent_file}'
            if os.path.exists(agent_path):
                print(f"✓ {agent_file} exists")
            else:
                print(f"✗ {agent_file} missing")
                
    except Exception as e:
        print(f"✗ Agents import failed: {e}")
    
    print("\nTesting tools structure...")
    try:
        import tools
        print("✓ Tools package imported")
        
        # Check if tool files exist
        tool_files = ['crm_lookup_tool.py', 'transcript_retrieval_tool.py', 
                     'policy_lookup_tool.py', 'payment_tools.py', 
                     'communication_tools.py']
        for tool_file in tool_files:
            tool_path = f'tools/{tool_file}'
            if os.path.exists(tool_path):
                print(f"✓ {tool_file} exists")
            else:
                print(f"✗ {tool_file} missing")
                
    except Exception as e:
        print(f"✗ Tools import failed: {e}")
    
    print("\nTesting knowledge base...")
    try:
        kb_file = 'knowledge_base/prepare_knowledge_base.py'
        if os.path.exists(kb_file):
            print("✓ Knowledge base preparation script exists")
        else:
            print("✗ Knowledge base script missing")
    except Exception as e:
        print(f"✗ Knowledge base test failed: {e}")
    
    print("\nTesting configuration files...")
    config_files = ['requirements.txt', 'Dockerfile', 'setup-gcp.sh', 'README.md']
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"✓ {config_file} exists")
        else:
            print(f"✗ {config_file} missing")

if __name__ == "__main__":
    print("Customer Experience Rescue Swarm - Structure Test")
    print("=" * 50)
    test_imports()
    print("\n" + "=" * 50)
    print("Structure test completed!")