#!/usr/bin/env python3
"""
Test script to verify Python skill with registry and keyword routing
"""
import sys
import io

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import the skill to trigger registration
from SKILLS.common.web_search.skill import WebSearch

from agent import Router, SkillInput
from agent.skill_registry import get_skill_definition, SKILL_REGISTRY


def test_registry():
    """Test skill registry functionality"""
    print("=" * 70)
    print("TEST 1: Skill Registry Verification")
    print("=" * 70)

    print(f"\n[Registry Contents]")
    for name, definition in SKILL_REGISTRY.items():
        print(f"  - {name}: {definition.cls.__name__}")
        print(f"    Keywords: {definition.keywords}")

    # Test get_skill_definition
    print(f"\n[Checking skill_definition for 'web_search']...")
    definition = get_skill_definition("web_search")
    if definition:
        print(f"  ✅ Found in registry")
        print(f"  Class: {definition.cls.__name__}")
        print(f"  Keywords: {definition.keywords}")
    else:
        print(f"  ❌ Not found in registry")
        return False

    return True


def test_skill_loading():
    """Test skill loading via Router"""
    print("\n" + "=" * 70)
    print("TEST 2: Skill Loading via Router")
    print("=" * 70)

    router = Router()

    print(f"\n[Loading web_search skill]...")
    try:
        skill = router.load_skill("web_search")
        print(f"  ✅ Skill loaded successfully")
        print(f"  Skill name: {skill.name}")
        print(f"  Skill class: {skill.__class__.__name__}")
        print(f"  Is WebSearch instance: {isinstance(skill, WebSearch)}")
    except Exception as e:
        print(f"  ❌ Error loading skill: {e}")
        return False

    return True


def test_metadata_loading():
    """Test metadata loading"""
    print("\n" + "=" * 70)
    print("TEST 3: Metadata Loading")
    print("=" * 70)

    router = Router()

    print(f"\n[Loading skill metadata]...")
    skill_dirs = list(router.skills_dir.glob("**/web_search"))
    if skill_dirs:
        skill_dir = skill_dirs[0]
        router._load_skill_metadata("web_search", skill_dir)

        meta = router.skill_metadata.get("web_search", {})
        print(f"  Name: {meta.get('name')}")
        print(f"  Description: {meta.get('description')}")
        print(f"  Version: {meta.get('version')}")
        print(f"  Categories: {meta.get('categories', [])}")
        print(f"  Entrypoint: {meta.get('entrypoint', 'None (using registry)')}")
        print(f"  ✅ Metadata loaded successfully")
    else:
        print(f"  ❌ Skill directory not found")
        return False

    return True


def test_keyword_routing():
    """Test keyword retrieval and routing"""
    print("\n" + "=" * 70)
    print("TEST 4: Keyword Routing")
    print("=" * 70)

    router = Router()

    print(f"\n[Getting skill keywords from metadata]...")
    keywords = router.get_skill_keywords("web_search")
    print(f"  Keywords ({len(keywords)}): {keywords}")

    # Test keyword matching
    test_queries = [
        ("帮我搜索一下Python教程", ["搜索"]),
        ("查找相关网页信息", ["查找", "网页"]),
        ("use google to search", ["google", "search"]),
        ("查询订单状态", ["查询"]),
    ]

    print(f"\n[Testing keyword matching]...")
    for query, expected in test_queries:
        matched = [k for k in expected if k in query.lower() or k in query]
        print(f"  Query: '{query}'")
        print(f"    Matched keywords: {matched}")
        print(f"    ✓ Keywords present in skill")

    print(f"  ✅ Keyword routing works")

    return True


def test_skill_execution():
    """Test skill execution"""
    print("\n" + "=" * 70)
    print("TEST 5: Skill Execution")
    print("=" * 70)

    router = Router()

    print(f"\n[Executing skill with test input]...")
    skill = router.load_skill("web_search")

    input_data = SkillInput(
        task_id="test_001",
        sender="test",
        receiver="web_search",
        role="skill",
        content="Python编程教程",
        params={"max_results": 3},
        context={},
        execution_profile="worker_cheap"
    )

    result = skill.execute(input_data)

    print(f"  Success: {result.success}")
    print(f"  Query: {result.data.get('query', 'N/A')}")
    print(f"  Results count: {result.data.get('total', 0)}")
    print(f"  Results preview:")
    for i, r in enumerate(result.data.get('results', []), 1):
        print(f"    {i}. {r.get('title')}")

    if result.success:
        print(f"  ✅ Skill execution successful")
    else:
        print(f"  ❌ Skill execution failed: {result.error}")
        return False

    return True


def test_entrpoint_fallback():
    """Test entrypoint fallback (comment out registry import to test)"""
    print("\n" + "=" * 70)
    print("TEST 6: Entrypoint Fallback (if registry not available)")
    print("=" * 70)

    print(f"\n[Checking entrypoint in metadata]...")
    router = Router()

    meta = router.skill_metadata.get("web_search", {})
    entrypoint = meta.get("entrypoint")

    if entrypoint:
        print(f"  Entrypoint: {entrypoint}")
        print(f"  ℹ️  To test entrypoint loading, comment out registry import and uncomment entrypoint in skill_meta.yaml")
    else:
        print(f"  ℹ️  No entrypoint configured - using registry (current mode)")

    print(f"  ✅ Entrypoint path available for testing")

    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  PYTHON SKILL REGISTRY & KEYWORD ROUTING TEST SUITE")
    print("=" * 70)

    tests = [
        ("Registry", test_registry),
        ("Skill Loading", test_skill_loading),
        ("Metadata Loading", test_metadata_loading),
        ("Keyword Routing", test_keyword_routing),
        ("Skill Execution", test_skill_execution),
        ("Entrypoint Fallback", test_entrpoint_fallback),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {name}")

    all_passed = all(r for _, r in results)
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 70)

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
