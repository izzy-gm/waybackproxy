#!/bin/bash
################################################################################
# WaybackProxy Installation Verification Script
# Tests that the new architecture is properly installed and functional
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_test() { echo -e "\n${YELLOW}Testing:${NC} $1"; }

ERRORS=0

echo "=============================================="
echo "WaybackProxy Installation Verification"
echo "=============================================="
echo ""

################################################################################
# Test Python installation
################################################################################

log_test "Python 3.12+ installation"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [ "$(printf '%s\n' "3.12" "$PYTHON_VERSION" | sort -V | head -n1)" = "3.12" ]; then
        log_info "Python $PYTHON_VERSION detected (>= 3.12 required)"
    else
        log_warn "Python $PYTHON_VERSION detected (3.12+ recommended)"
    fi
else
    log_error "Python 3 not found"
    ERRORS=$((ERRORS+1))
fi

################################################################################
# Test package structure
################################################################################

log_test "Package structure"
if [ -d "src/waybackproxy" ]; then
    log_info "src/waybackproxy/ directory exists"

    # Check for key modules
    REQUIRED_MODULES=(
        "src/waybackproxy/__init__.py"
        "src/waybackproxy/__main__.py"
        "src/waybackproxy/core/handler.py"
        "src/waybackproxy/config/settings.py"
        "src/waybackproxy/hardware/gpio.py"
        "src/waybackproxy/ui/controller.py"
    )

    for module in "${REQUIRED_MODULES[@]}"; do
        if [ -f "$module" ]; then
            log_info "$(basename $module) present"
        else
            log_error "Missing: $module"
            ERRORS=$((ERRORS+1))
        fi
    done
else
    log_error "src/waybackproxy/ directory not found"
    ERRORS=$((ERRORS+1))
fi

################################################################################
# Test packaging files
################################################################################

log_test "Packaging configuration"
if [ -f "pyproject.toml" ]; then
    log_info "pyproject.toml present"
else
    log_error "pyproject.toml missing"
    ERRORS=$((ERRORS+1))
fi

if [ -f "setup.py" ]; then
    log_info "setup.py present"
else
    log_error "setup.py missing"
    ERRORS=$((ERRORS+1))
fi

################################################################################
# Test configuration files
################################################################################

log_test "Configuration files"
if [ -f "config.sample.json" ]; then
    log_info "config.sample.json present"

    # Validate JSON
    if command -v python3 &> /dev/null; then
        if python3 -c "import json; json.load(open('config.sample.json'))" 2>/dev/null; then
            log_info "config.sample.json is valid JSON"
        else
            log_error "config.sample.json is invalid JSON"
            ERRORS=$((ERRORS+1))
        fi
    fi
else
    log_error "config.sample.json missing"
    ERRORS=$((ERRORS+1))
fi

################################################################################
# Test scripts
################################################################################

log_test "Installation scripts"
REQUIRED_SCRIPTS=(
    "scripts/install.sh"
    "scripts/setup-gateway.sh"
    "scripts/disable-gateway.sh"
)

for script in "${REQUIRED_SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            log_info "$(basename $script) present and executable"
        else
            log_warn "$(basename $script) present but not executable"
        fi
    else
        log_error "Missing: $script"
        ERRORS=$((ERRORS+1))
    fi
done

################################################################################
# Test Python imports (if package is installed)
################################################################################

log_test "Python package imports"
if command -v python3 &> /dev/null; then
    # Check if package is installed
    if python3 -c "import waybackproxy" 2>/dev/null; then
        log_info "waybackproxy package is importable"

        # Test key imports
        IMPORTS=(
            "waybackproxy.config"
            "waybackproxy.core"
            "waybackproxy.hardware"
            "waybackproxy.ui"
            "waybackproxy.utils"
        )

        for import in "${IMPORTS[@]}"; do
            if python3 -c "import ${import}" 2>/dev/null; then
                log_info "${import} imports successfully"
            else
                log_error "${import} failed to import"
                ERRORS=$((ERRORS+1))
            fi
        done

        # Test CLI entry point
        if command -v waybackproxy &> /dev/null; then
            log_info "waybackproxy CLI command available"
        else
            log_warn "waybackproxy CLI command not in PATH"
        fi

        # Test --help flag
        if python3 -m waybackproxy --help &> /dev/null; then
            log_info "python -m waybackproxy works"
        else
            log_error "python -m waybackproxy failed"
            ERRORS=$((ERRORS+1))
        fi

    else
        log_warn "waybackproxy package not installed (run: pip install -e .)"
        log_warn "Skipping import tests"
    fi
fi

################################################################################
# Test for legacy files (should not exist)
################################################################################

log_test "Legacy file cleanup"
LEGACY_FILES=(
    "waybackproxy.py"
    "init.py"
    "config.py"
    "config_handler.py"
    "DateChanger.py"
    "RotaryEncoder.py"
    "KeyCapture.py"
    "RGB1602.py"
    "lrudict.py"
    "encoder_test.py"
)

LEGACY_FOUND=0
for file in "${LEGACY_FILES[@]}"; do
    if [ -f "$file" ]; then
        log_error "Legacy file still exists: $file"
        LEGACY_FOUND=1
        ERRORS=$((ERRORS+1))
    fi
done

if [ $LEGACY_FOUND -eq 0 ]; then
    log_info "No legacy files found (clean)"
fi

################################################################################
# Summary
################################################################################

echo ""
echo "=============================================="
if [ $ERRORS -eq 0 ]; then
    log_info "ALL TESTS PASSED ✓"
    echo "=============================================="
    echo ""
    echo "Installation appears to be correct."
    echo ""
    echo "Next steps:"
    echo "  1. Install package: pip install -e ."
    echo "  2. Run headless: waybackproxy --headless"
    echo "  3. Run with UI: waybackproxy"
    echo ""
    exit 0
else
    log_error "$ERRORS TEST(S) FAILED ✗"
    echo "=============================================="
    echo ""
    echo "Please fix the errors above before deploying."
    echo ""
    exit 1
fi
