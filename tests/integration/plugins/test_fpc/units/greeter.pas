unit greeter;

interface

function Greeting: string;

implementation

uses
  SysUtils;

{$I greeting.inc}

function Greeting: string;
begin
{$IFDEF LOUD}
  Greeting := UpperCase(GreetingText);
{$ELSE}
  Greeting := GreetingText;
{$ENDIF}
end;

end.
