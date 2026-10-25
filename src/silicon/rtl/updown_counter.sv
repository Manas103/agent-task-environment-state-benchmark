// Original to this repo (not sourced from any external project). A small 4-bit synchronous
// up/down counter with enable, used as the fixed DUT for the coverage-hole-stimulus and
// assertion-completion task families in the silicon-design benchmark extension.
module updown_counter (
  input  logic       clk_i,
  input  logic       rst_ni,
  input  logic       en_i,
  input  logic       up_down_i,  // 1 = count up, 0 = count down
  output logic [3:0] count_o
);
  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      count_o <= 4'd0;
    end else if (en_i) begin
      if (up_down_i) begin
        count_o <= count_o + 4'd1;
      end else begin
        count_o <= count_o - 4'd1;
      end
    end
  end
endmodule
