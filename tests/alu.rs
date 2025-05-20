// file: tests/simple_test.rs
use marlin::verilator::{VerilatorRuntime, VerilatorRuntimeOptions};
use snafu::Whatever;
use very_holy_core::Alu;

fn runtime() -> Result<VerilatorRuntime, Whatever> {
    VerilatorRuntime::new(
        "target/marlin".into(),
        &[
            "target/veryl/types.sv".as_ref(),
            "target/veryl/alu.sv".as_ref(),
        ],
        &["target/veryl".as_ref()],
        [],
        VerilatorRuntimeOptions::default(),
    )
}

#[test]
#[snafu::report]
fn alu() -> Result<(), Whatever> {
    let runtime = runtime()?;
    let mut dut = runtime.create_model_simple::<Alu>()?;

    println!("{}", std::env::current_dir().unwrap().to_str().unwrap());
    let mut vcd = dut.open_vcd("foo.vcd");
    vcd.dump(0);

    dut.alu_control = 0b1111;
    dut.src1 = 0xFFFF;
    dut.src2 = 0xFFFF;
    dut.eval();
    assert_eq!(dut.alu_result, 0);

    vcd.dump(1);
    println!("Dumped");
    vcd.flush();

    Ok(())
}
