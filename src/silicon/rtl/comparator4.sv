// Original to this repo. A small 4-bit magnitude comparator, used as the fixed golden
// reference for the specification-to-RTL task family's Yosys equivalence check.
module comparator4 (
  input  logic [3:0] a_i,
  input  logic [3:0] b_i,
  output logic        gt_o,
  output logic        eq_o,
  output logic        lt_o
);
  assign gt_o = a_i > b_i;
  assign eq_o = a_i == b_i;
  assign lt_o = a_i < b_i;
endmodule
