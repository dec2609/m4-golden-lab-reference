import { useEffect, useRef } from "react";
import { createRequestScope } from "../services/requestScope";

export function useRequestScope() {
  const scope = useRef(createRequestScope()).current;
  useEffect(() => () => scope.cancel(), [scope]);
  return scope;
}
