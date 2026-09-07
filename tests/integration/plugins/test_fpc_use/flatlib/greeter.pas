unit greeter;

interface

function Greeting: string;

implementation

function Greeting: string;
begin
  Greeting := 'Hello from the flat library!';
end;

end.
