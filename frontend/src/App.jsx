import { Link, Navigate, Route, Routes } from "react-router-dom";
import EvaluatePage from "./pages/EvaluatePage";
import AuctionListPage from "./pages/AuctionListPage";
import AuctionDetailPage from "./pages/AuctionDetailPage";

export default function App() {
  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="logo">
          Car Estimate
        </Link>
        <nav>
          <Link to="/">Оценка</Link>
          <Link to="/auction">Аукцион</Link>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<EvaluatePage />} />
          <Route path="/auction" element={<AuctionListPage />} />
          <Route path="/auction/:id" element={<AuctionDetailPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
