package org.starcraft.printer;

import org.starcraft.add.Adder;

public class AdditionPrinter {
  public String print(int value1, int value2) {
    Adder adder = new Adder();
    int sum = adder.add(value1, value2);
    return String.format("%d plus %d equals %d", value1, value2, sum);
  }
}

