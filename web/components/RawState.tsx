import type { QueryResponse } from "@/lib/api";
import { Expander } from "@/components/ui/Expander";

export interface RawStateProps {
  state: QueryResponse;
}

export function RawState({ state }: RawStateProps) {
  return (
    <Expander summary="原始 state（调试）">
      <pre className="text-[0.78rem] font-mono text-[#c3cbe6] overflow-auto max-h-96 whitespace-pre-wrap break-all">
        {JSON.stringify(state, null, 2)}
      </pre>
    </Expander>
  );
}
