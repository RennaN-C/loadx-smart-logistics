import { Component, type ReactNode } from "react";
import { AlertBanner } from "../../../components/AlertBanner";

/** A WebGL failure must not hide metrics, the volume table or operational actions. */
export class SceneBoundary extends Component<{ readonly children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return <div className="viewer-scene-error"><AlertBanner>Não foi possível abrir o 3D neste navegador. Os dados da carga continuam disponíveis na tabela de volumes. Verifique o suporte a WebGL ou tente novamente.</AlertBanner><button className="btn-secondary" type="button" onClick={() => this.setState({ failed: false })}>Tentar abrir o 3D novamente</button></div>;
    return this.props.children;
  }
}
