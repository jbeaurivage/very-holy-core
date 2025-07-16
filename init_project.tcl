set projDir "./vivado"
set projName "very_holy_core"
set topName top
set device xc7a35tftg256-1
if {[file exists "$projDir"]} { file delete -force "$projDir" }
create_project $projName "$projDir" -part $device
set_property design_mode RTL [get_filesets sources_1]

# Initialize empty list for all SystemVerilog files
set filelist "./very_holy_core.f"
set verilogSources [list]

set fp [open $filelist r]
while {[gets $fp line] >= 0} {
    # Skip empty lines, comments and test files
    if {[string trim $line] eq "" || [string match "#*" $line]} {
        continue
    }
    lappend verilogSources $line
}
close $fp

add_files -fileset [get_filesets sources_1] -force -norecurse $verilogSources
set xdcSources [list "./fpga/alchrity_au/constraints.xdc" "./fpga/alchrity_au/au_props.xdc" ]
read_xdc $xdcSources
set_property STEPS.WRITE_BITSTREAM.ARGS.BIN_FILE true [get_runs impl_1]
update_compile_order -fileset sources_1

# Veryl generics creates a bunch of top modules.
# Let's select the correct one.
set_property top very_holy_core_au_top [current_fileset]

# Generate clocking wizard
source "./fpga/clk_wiz.tcl"

start_gui