#!/usr/bin/env python3
"""Quick test to verify ViewModels work correctly."""

from src.ui.viewmodels import ExperimentViewModel, BatchViewModel, ActiveUserViewModel

def test_experiment_viewmodel():
    """Test ExperimentViewModel."""
    vm = ExperimentViewModel(1, "Test Experiment", max_turns=5)
    
    assert vm.id == 1
    assert vm.name == "Test Experiment"
    assert vm.expected_messages == 10  # 5 turns * 2
    assert vm.status == 'queued'
    assert vm.status_icon == '⏳'
    
    # Update status
    vm.status = 'running'
    assert vm.status_icon == '🔄'
    
    vm.status = 'completed'
    assert vm.status_icon == '✓'
    assert vm.status_with_name == '✓ Test Experiment'
    
    # Update message count
    vm.msg_count = 5
    assert vm.progress_text == '5/10 messages'
    
    print("✅ ExperimentViewModel tests passed!")


def test_batch_viewmodel():
    """Test BatchViewModel."""
    vm = BatchViewModel(1, "Test Batch", total_experiments=25)
    
    assert vm.id == 1
    assert vm.name == "Test Batch"
    assert vm.total == 25
    assert vm.progress == 0.0
    
    # Update counts
    vm.completed = 10
    vm.running = 5
    vm.queued = 8
    vm.failed = 2
    
    assert vm.progress == 0.4  # 10/25
    assert "40.0%" in vm.progress_text
    assert "10/25" in vm.progress_text
    
    # Full completion
    vm.completed = 25
    assert vm.progress == 1.0
    
    print("✅ BatchViewModel tests passed!")


def test_active_user_viewmodel():
    """Test ActiveUserViewModel."""
    vm = ActiveUserViewModel(1, "Alice")
    
    assert vm.id == 1
    assert vm.display_name == "Alice"
    assert vm.activity == 'idle'
    assert vm.activity_icon == '👀'
    
    # Running experiments
    vm.activity = 'running'
    vm.experiment_count = 3
    assert vm.activity_icon == '🔄'
    assert vm.status_text == 'Running 3 experiments'
    
    # Viewing page
    vm.activity = 'viewing'
    vm.current_page = '/experiments'
    assert vm.status_text == 'Viewing /experiments'
    
    print("✅ ActiveUserViewModel tests passed!")


if __name__ == '__main__':
    test_experiment_viewmodel()
    test_batch_viewmodel()
    test_active_user_viewmodel()
    print("\n🎉 All ViewModel tests passed!")
