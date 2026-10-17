#!/bin/bash
# Manual mutation testing for refresh checks

echo "================================================================================"
echo "MUTATION TESTING: Refresh Checks"
echo "================================================================================"
echo "Testing that each check causes the build to exit non-zero on bad input"
echo ""

cd /workspace/backend

# Backup files
cp build_registry.py build_registry.py.bak
cp build_operators.py build_operators.py.bak
cp build_ccip_registry.py build_ccip_registry.py.bak
cp data/operator_overrides.json data/operator_overrides.json.bak

echo "================================================================================"
echo "Test 1: RDD non-200 response (build_registry.py)"
echo "================================================================================"
echo "Mutant: Set RDD response code to 404"
echo ""

# Apply mutation
sed -i 's/http_responses\[f"{RDD_BASE}\/{rdd_file}\.json"\] = resp\.status_code/http_responses[f"{RDD_BASE}\/{rdd_file}.json"] = 404  # MUTANT/' build_registry.py

# Run build
echo "Running build_registry.py..."
if python3 build_registry.py > /tmp/test1_out.txt 2>&1; then
    echo "❌ FAIL: Build succeeded but should have failed"
    tail -20 /tmp/test1_out.txt
    RESULT1="FAIL"
else
    echo "✓ Build failed as expected (exit $?)"
    grep -A 2 "REFRESH CHECK FAILED" /tmp/test1_out.txt | head -5
    RESULT1="PASS"
fi

# Revert
cp build_registry.py.bak build_registry.py
echo ""

echo "================================================================================"
echo "Test 2: Mapping rate below 98% (build_operators.py)"
echo "================================================================================"
echo "Mutant: Lower mapping threshold to trigger failure"
echo ""

# Apply mutation - change threshold to 99.6% which will fail for ethereum (99.5%)
sed -i 's/threshold=98\.0/threshold=99.6/' build_operators.py

echo "Running build_operators.py..."
if python3 build_operators.py > /tmp/test2_out.txt 2>&1; then
    echo "❌ FAIL: Build succeeded but should have failed"
    tail -20 /tmp/test2_out.txt
    RESULT2="FAIL"
else
    echo "✓ Build failed as expected (exit $?)"
    grep -A 2 "REFRESH CHECK FAILED" /tmp/test2_out.txt | head -5
    RESULT2="PASS"
fi

# Revert
cp build_operators.py.bak build_operators.py
echo ""

echo "================================================================================"
echo "Test 3: RPC failure rate > 30% (build_operators.py)"
echo "================================================================================"
echo "Mutant: Lower RPC failure threshold to trigger failure"
echo ""

# Apply mutation - set threshold to 0% to trigger on any failures
sed -i 's/max_failure_pct=30\.0/max_failure_pct=0.0/' build_operators.py

echo "Running build_operators.py..."
if python3 build_operators.py > /tmp/test3_out.txt 2>&1; then
    echo "⚠ Build succeeded (no RPC failures in this run)"
    RESULT3="N/A"
else
    echo "✓ Build failed as expected (exit $?)"
    grep -A 2 "REFRESH CHECK FAILED" /tmp/test3_out.txt | head -5
    RESULT3="PASS"
fi

# Revert
cp build_operators.py.bak build_operators.py
echo ""

echo "================================================================================"
echo "Test 4: Feed count change > 20% (pytest)"
echo "================================================================================"
echo "Testing via pytest only (no build mutation needed)"
echo ""

python3 -m pytest test_refresh_checks.py::test_check_feed_count_change_fails_above_20_percent -v > /tmp/test4_out.txt 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Test passes"
    RESULT4="PASS"
else
    echo "❌ Test failed"
    tail -10 /tmp/test4_out.txt
    RESULT4="FAIL"
fi
echo ""

echo "================================================================================"
echo "Test 5: Hidden operators leak as public (build_operators.py)"
echo "================================================================================"
echo "Mutant: Remove 'cl-ocr-nav-' from hidden patterns"
echo ""

# Apply mutation
sed -i '/"cl-ocr-nav-",/d' data/operator_overrides.json

echo "Running build_operators.py..."
if python3 build_operators.py > /tmp/test5_out.txt 2>&1; then
    echo "❌ FAIL: Build succeeded but should have failed"
    # Check if hidden operators leaked
    OPS_COUNT=$(python3 -c "import json; print(len(json.loads(open('data/operators.json').read())['operators']))" 2>/dev/null || echo "unknown")
    echo "Operators count: $OPS_COUNT (should be >43 if internals leaked)"
    tail -20 /tmp/test5_out.txt
    RESULT5="FAIL"
else
    echo "✓ Build failed as expected (exit $?)"
    grep -A 2 "REFRESH CHECK FAILED" /tmp/test5_out.txt | head -5
    RESULT5="PASS"
fi

# Revert
cp data/operator_overrides.json.bak data/operator_overrides.json
cp build_operators.py.bak build_operators.py  # In case it was modified
echo ""

echo "================================================================================"
echo "Test 6: CCIP API non-200 response (build_ccip_registry.py)"
echo "================================================================================"
echo "Mutant: Set CCIP API response code to 500"
echo ""

# Apply mutation
sed -i 's/http_responses\[MAINNET_API_URL\] = mainnet_status/http_responses[MAINNET_API_URL] = 500  # MUTANT/' build_ccip_registry.py

echo "Running build_ccip_registry.py..."
if python3 build_ccip_registry.py > /tmp/test6_out.txt 2>&1; then
    echo "❌ FAIL: Build succeeded but should have failed"
    tail -20 /tmp/test6_out.txt
    RESULT6="FAIL"
else
    echo "✓ Build failed as expected (exit $?)"
    grep -A 2 "REFRESH CHECK FAILED" /tmp/test6_out.txt | head -5
    RESULT6="PASS"
fi

# Revert
cp build_ccip_registry.py.bak build_ccip_registry.py
echo ""

# Clean up backups
rm -f build_registry.py.bak build_operators.py.bak build_ccip_registry.py.bak data/operator_overrides.json.bak

# Summary table
echo "================================================================================"
echo "MUTATION TESTING SUMMARY"
echo "================================================================================"
printf "%-50s %-30s %-10s\n" "Mutant" "Test/Build Script" "Result"
echo "--------------------------------------------------------------------------------"
printf "%-50s %-30s %-10s\n" "RDD non-200 response" "build_registry.py" "$RESULT1"
printf "%-50s %-30s %-10s\n" "Mapping rate below 98%" "build_operators.py" "$RESULT2"
printf "%-50s %-30s %-10s\n" "RPC failure rate > 30%" "build_operators.py" "$RESULT3"
printf "%-50s %-30s %-10s\n" "Feed count change > 20%" "pytest (refresh_checks)" "$RESULT4"
printf "%-50s %-30s %-10s\n" "Hidden operators leak" "build_operators.py" "$RESULT5"
printf "%-50s %-30s %-10s\n" "CCIP API non-200" "build_ccip_registry.py" "$RESULT6"
echo "================================================================================"
