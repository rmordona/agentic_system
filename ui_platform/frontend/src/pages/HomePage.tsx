import React from "react";
import PlatformLayout from "../layouts/PlatformLayout";
import { Card, CardContent } from "@/components/ui/card";

const HomePage = () => {
  return (
    <PlatformLayout>
      <div className="p-6">
        <Card>
          <CardContent>
            <h1 className="text-2xl font-bold mb-4">
              Welcome to the Context Engineering Platform
            </h1>
            <p className="text-gray-700">
              Use the tabs above to navigate between Home, Category, Mode, and Login. Switch
              between Engineering and Production mode to manage context or view conversation history.
            </p>
          </CardContent>
        </Card>
      </div>
    </PlatformLayout>
  );
};

export default HomePage;