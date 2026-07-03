import unittest

from proofbench.tasks.minif2f import extract_theorem_statement


class MiniF2FParserTests(unittest.TestCase):
    def test_extract_theorem_statement_strips_proof(self):
        source = """
theorem first : True :=
begin
  trivial,
end

theorem target
  (x : Nat) :
  x = x :=
begin
  rfl,
end

theorem next : True :=
begin
  trivial,
end
"""
        statement = extract_theorem_statement(source, "target")
        self.assertTrue(statement.startswith("theorem target"))
        self.assertIn("x = x", statement)
        self.assertNotIn("rfl", statement)
        self.assertIn("sorry", statement)


if __name__ == "__main__":
    unittest.main()
