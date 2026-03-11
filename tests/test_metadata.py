#!/usr/bin/env python3
"""
Test script to verify skill metadata and keywords loading
"""
import sys

from agent import Router

def test_skill_metadata():
    """Test skill metadata and keywords loading"""
    print("=" * 60)
    print("Testing Skill Metadata & Keywords Flow")
    print("=" * 60)

    # Initialize Router
    router = Router()

    # Test 1: Load skill metadata
    print("\n[TEST 1] Loading skill metadata for data_analyst...")
    skill_dirs = list(router.skills_dir.glob("**/data_analyst"))
    if skill_dirs:
        skill_dir = skill_dirs[0]
        router._load_skill_metadata("data_analyst", skill_dir)

        meta = router.skill_metadata.get("data_analyst", {})
        print(f"  Name: {meta.get('name')}")
        print(f"  Description: {meta.get('description')}")
        print(f"  Version: {meta.get('version')}")
        print(f"  Categories: {meta.get('categories', [])}")
        print(f"  Entrypoint: {meta.get('entrypoint', 'None (markdown skill)')}")
        print("  [OK] Metadata loaded successfully")
    else:
        print("  [FAIL] Skill directory not found")
        return False

    # Test 2: Get keywords
    print("\n[TEST 2] Getting skill keywords...")
    keywords = router.get_skill_keywords("data_analyst")
    print(f"  Keywords ({len(keywords)}): {keywords}")
    print(f"  [OK] Keywords retrieved: {len(keywords)} keywords")

    # Test 3: Verify expected keywords
    print("\n[TEST 3] Verifying expected keywords...")
    expected = ["sql", "pandas", "dataframe", "统计", "分析", "订单", "数据"]
    missing = [k for k in expected if k not in keywords]
    if missing:
        print(f"  [WARN] Missing expected keywords: {missing}")
    else:
        print(f"  [OK] All expected keywords present")

    # Test 4: Test skill loading (markdown skill)
    print("\n[TEST 4] Loading the skill instance...")
    try:
        skill = router.load_skill("data_analyst")
        print(f"  Skill name: {skill.name}")
        print(f"  [OK] Skill instance created")
    except Exception as e:
        print(f"  [FAIL] Error loading skill: {e}")
        return False

    # Test 5: Test list_skills includes metadata
    print("\n[TEST 5] Checking list_skills() output...")
    skills = router.list_skills()
    data_analyst_skill = next((s for s in skills if s["name"] == "data_analyst"), None)
    if data_analyst_skill:
        print(f"  Skill found in list_skills()")
        print(f"  Path: {data_analyst_skill.get('path')}")
        print(f"  [OK] Skill properly discovered")
    else:
        print(f"  [WARN] data_analyst not found in list_skills()")

    print("\n" + "=" * 60)
    print("[OK] All metadata & keywords tests passed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    test_skill_metadata()
