import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge, EmptyState } from "./ui";

describe("StatusBadge", () => {
  it("renders the status text", () => {
    render(<StatusBadge status="in_progress" />);
    expect(screen.getByText("in progress")).toBeTruthy();
  });

  it("uses the success tone for done", () => {
    const { container } = render(<StatusBadge status="done" />);
    expect(container.querySelector(".badge-success")).toBeTruthy();
  });
});

describe("EmptyState", () => {
  it("renders title and detail", () => {
    render(<EmptyState title="No notes" detail="Start by creating one" />);
    expect(screen.getByText("No notes")).toBeTruthy();
    expect(screen.getByText("Start by creating one")).toBeTruthy();
  });
});
