import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import MappingView from "./pages/MappingView";
import PipelineView from "./pages/PipelineView";
import DatasetsView from "./pages/DatasetsView";
import EvaluationView from "./pages/EvaluationView";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<MappingView />} />
          <Route path="pipeline" element={<PipelineView />} />
          <Route path="evaluation" element={<EvaluationView />} />
          <Route path="datasets" element={<DatasetsView />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
