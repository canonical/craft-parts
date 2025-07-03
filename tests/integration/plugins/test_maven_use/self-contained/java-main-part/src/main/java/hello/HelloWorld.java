package org.starcraft.hello;

import org.starcraft.printer.AdditionPrinter;

public class HelloWorld {
  public static void main(String[] args) {
    AdditionPrinter printer = new AdditionPrinter();
    System.out.println(printer.print(1, 1));
  }
}

