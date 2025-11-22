# frozen_string_literal: true
Gem::Specification.new do |spec|
  spec.name          = "test_ruby"
  spec.version       = "0.0.1"
  spec.summary       = "Test the ruby plugin"
  spec.authors       = ["Canonical Ltd."]
  spec.email         = ["snapcraft@lists.snapcraft.io"]
  spec.license       = "GPLv3"
  spec.files         = Dir["lib/**/*.rb", "exe/*"]
  spec.bindir        = "exe"
  spec.executables   = ["mytest"]
  spec.require_paths = ["lib"]
end
