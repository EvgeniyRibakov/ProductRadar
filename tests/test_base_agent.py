"""Tests for BaseAgent"""

import pytest
from src.agents.base_agent import BaseAgent


class TestAgent(BaseAgent):
    """Тестовый агент для проверки базового функционала"""
    
    async def run(self, task: str, **kwargs):
        return f"Running task: {task}"
    
    async def process(self, input_data):
        return f"Processed: {input_data}"


@pytest.mark.asyncio
async def test_agent_initialization():
    """Тест инициализации агента"""
    agent = TestAgent()
    assert agent.config == {}


@pytest.mark.asyncio
async def test_agent_with_config():
    """Тест агента с конфигурацией"""
    config = {"test_key": "test_value"}
    agent = TestAgent(config=config)
    assert agent.config == config


@pytest.mark.asyncio
async def test_agent_run():
    """Тест выполнения задачи"""
    agent = TestAgent()
    result = await agent.run("test task")
    assert result == "Running task: test task"


@pytest.mark.asyncio
async def test_agent_process():
    """Тест обработки данных"""
    agent = TestAgent()
    result = await agent.process("test data")
    assert result == "Processed: test data"

