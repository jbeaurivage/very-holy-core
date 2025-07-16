alias t := test
alias ta := test-all
alias b := build
alias c := check

vivado:
    veryl build --quiet
    vivado -nolog -nojournal -mode tcl -source {{justfile_directory()}}/init_project.tcl

wave file:
    surfer {{justfile_directory()}}/target/waveform/{{file}}.fst >& /dev/null & 

build:
    veryl build --quiet

check:
    veryl check --quiet

fmt:
    veryl fmt --quiet

clean:
    veryl clean --quiet
    rm -rf \
        {{justfile_directory()}}/.build \
        {{justfile_directory()}}/.Xil \
        {{justfile_directory()}}/dependencies \
        {{justfile_directory()}}/target \
        {{justfile_directory()}}/vivado \
        {{justfile_directory()}}/very_holy_core.f

test TEST *extra_args:
    veryl test {{justfile_directory()}}/src/tests/test_{{TEST}}.veryl \
        {{justfile_directory()}}/src/*.veryl \
        {{justfile_directory()}}/src/tests/common/*.veryl \
        {{justfile_directory()}}/src/peripherals/*.veryl \
        {{justfile_directory()}}/src/cpu/*.veryl \
        {{justfile_directory()}}/src/memory/*.veryl \
        {{justfile_directory()}}/src/cpu/load_store/*.veryl \
        {{justfile_directory()}}/src/cpu/writeback/*.veryl \
        --wave --quiet {{extra_args}}

test-all:
    veryl test --wave --quiet
