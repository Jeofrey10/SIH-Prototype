import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DataTable, type Column } from "./DataTable";

interface TestItem {
  id: string;
  name: string;
  count: number;
}

describe("DataTable", () => {
  const columns: Column<TestItem>[] = [
    { header: "Name", accessorKey: "name", sortable: true },
    { header: "Count", accessorKey: "count", sortable: false },
  ];

  const data: TestItem[] = [
    { id: "1", name: "Engineering College A", count: 12 },
    { id: "2", name: "Polytechnic B", count: 5 },
  ];

  it("renders table headers and rows accurately", () => {
    render(<DataTable columns={columns} data={data} totalCount={2} />);
    expect(screen.getByText("Engineering College A")).toBeInTheDocument();
    expect(screen.getByText("Polytechnic B")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("renders empty state when data is empty and not loading", () => {
    render(
      <DataTable
        columns={columns}
        data={[]}
        totalCount={0}
        emptyTitle="Nothing here"
      />
    );
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
  });

  it("triggers onRowClick when a table row is clicked", () => {
    const handleRowClick = vi.fn();
    render(
      <DataTable
        columns={columns}
        data={data}
        totalCount={2}
        onRowClick={handleRowClick}
      />
    );
    fireEvent.click(screen.getByText("Engineering College A"));
    expect(handleRowClick).toHaveBeenCalledWith(data[0]);
  });
});
