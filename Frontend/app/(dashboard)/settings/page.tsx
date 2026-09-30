"use client";

import { useState } from "react";
import { User, Shield, Database, Key, Bell, Palette, Globe, Save, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Toast, ToastClose, ToastDescription, ToastProvider, ToastTitle, ToastViewport, useToast } from "@/components/ui/toast";
import { Toaster } from "@/components/ui/toaster";

const workspaces = ["prod", "staging", "dev"];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("profile");
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();

  // Form states
  const [profile, setProfile] = useState({
    name: "Admin User",
    email: "admin@agenticai.dev",
    avatar: null,
  });
  const [preferences, setPreferences] = useState({
    theme: "system",
    language: "en",
    timezone: "UTC",
    compactMode: false,
    animations: true,
  });
  const [notifications, setNotifications] = useState({
    email: true,
    push: true,
    costAlerts: true,
    healthAlerts: true,
    governanceAlerts: true,
    weeklyDigest: false,
  });
  const [security, setSecurity] = useState({
    twoFactor: false,
    sessionTimeout: 60,
    apiKeyRotation: 90,
  });

  const handleSave = async (section: string) => {
    setSaving(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setSaving(false);
    toast({
      title: "Saved",
      description: `${section} settings updated successfully`,
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">Manage your account, preferences, and workspace configuration</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="profile"><User className="h-4 w-4 mr-2" />Profile</TabsTrigger>
          <TabsTrigger value="preferences"><Palette className="h-4 w-4 mr-2" />Preferences</TabsTrigger>
          <TabsTrigger value="notifications"><Bell className="h-4 w-4 mr-2" />Notifications</TabsTrigger>
          <TabsTrigger value="security"><Shield className="h-4 w-4 mr-2" />Security</TabsTrigger>
          <TabsTrigger value="workspaces"><Database className="h-4 w-4 mr-2" />Workspaces</TabsTrigger>
        </TabsList>

        {/* Profile Tab */}
        <TabsContent value="profile">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Profile Information</CardTitle>
                <CardDescription>Update your personal information</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-6">
                  <Avatar className="h-20 w-20">
                    <AvatarImage src={profile.avatar || undefined} alt={profile.name} />
                    <AvatarFallback>{profile.name.charAt(0)}</AvatarFallback>
                  </Avatar>
                  <div>
                    <Label>Display Name</Label>
                    <Input value={profile.name} onChange={e => setProfile(p => ({ ...p, name: e.target.value }))} />
                    <Label className="mt-4">Email</Label>
                    <Input value={profile.email} onChange={e => setProfile(p => ({ ...p, email: e.target.value }))} disabled />
                    <p className="text-sm text-muted-foreground mt-1">Email cannot be changed</p>
                  </div>
                </div>
                <Button onClick={() => handleSave("Profile")} disabled={saving}>
                  {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                  Save Changes
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>API Keys</CardTitle>
                <CardDescription>Manage your personal API keys</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 border rounded-lg">
                    <div>
                      <p className="font-medium">Production OpenAI</p>
                      <p className="text-sm text-muted-foreground">sk-prod-... • Expires Apr 15, 2024</p>
                    </div>
                    <Badge variant="default">Active</Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 border rounded-lg">
                    <div>
                      <p className="font-medium">Staging Anthropic</p>
                      <p className="text-sm text-muted-foreground">sk-staging-... • Expires Mar 20, 2024</p>
                    </div>
                    <Badge variant="default">Active</Badge>
                  </div>
                </div>
                <Button variant="outline" onClick={() => { /* open create key modal */ }}>
                  <Key className="h-4 w-4 mr-2" />
                  Create New API Key
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Preferences Tab */}
        <TabsContent value="preferences">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Appearance</CardTitle>
                <CardDescription>Customize how AgenticAI looks</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Theme</Label>
                  <Select value={preferences.theme} onValueChange={v => setPreferences(p => ({ ...p, theme: v }))}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="light">Light</SelectItem>
                      <SelectItem value="dark">Dark</SelectItem>
                      <SelectItem value="system">System</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Language</Label>
                  <Select value={preferences.language} onValueChange={v => setPreferences(p => ({ ...p, language: v }))}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="en">English</SelectItem>
                      <SelectItem value="es">Spanish</SelectItem>
                      <SelectItem value="fr">French</SelectItem>
                      <SelectItem value="de">German</SelectItem>
                      <SelectItem value="ja">Japanese</SelectItem>
                      <SelectItem value="zh">Chinese</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Timezone</Label>
                  <Select value={preferences.timezone} onValueChange={v => setPreferences(p => ({ ...p, timezone: v }))}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="UTC">UTC</SelectItem>
                      <SelectItem value="America/New_York">Eastern Time</SelectItem>
                      <SelectItem value="America/Chicago">Central Time</SelectItem>
                      <SelectItem value="America/Denver">Mountain Time</SelectItem>
                      <SelectItem value="America/Los_Angeles">Pacific Time</SelectItem>
                      <SelectItem value="Europe/London">London</SelectItem>
                      <SelectItem value="Europe/Paris">Paris</SelectItem>
                      <SelectItem value="Asia/Tokyo">Tokyo</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Compact Mode</Label>
                    <p className="text-sm text-muted-foreground">Reduce spacing for more content</p>
                  </div>
                  <Switch checked={preferences.compactMode} onCheckedChange={c => setPreferences(p => ({ ...p, compactMode: c }))} />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Animations</Label>
                    <p className="text-sm text-muted-foreground">Enable UI transitions and animations</p>
                  </div>
                  <Switch checked={preferences.animations} onCheckedChange={c => setPreferences(p => ({ ...p, animations: c }))} />
                </div>
                <Button onClick={() => handleSave("Preferences")} disabled={saving}>
                  {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                  Save Changes
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Default Workspace</CardTitle>
                <CardDescription>Set your default workspace context</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Default Workspace</Label>
                  <Select>
                    <SelectTrigger><SelectValue placeholder="Select workspace" /></SelectTrigger>
                    <SelectContent>
                      {workspaces.map(w => <SelectItem key={w} value={w}>{w}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Default Integration Set</Label>
                  <Select>
                    <SelectTrigger><SelectValue placeholder="Select integration set" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="minimal">Minimal (Core only)</SelectItem>
                      <SelectItem value="standard">Standard (Recommended)</SelectItem>
                      <SelectItem value="full">Full (All integrations)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={() => handleSave("Workspace")} disabled={saving}>
                  {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                  Save Changes
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications">
          <Card>
            <CardHeader>
              <CardTitle>Notification Preferences</CardTitle>
              <CardDescription>Choose what notifications you receive</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-4">
                {Object.entries(notifications).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between">
                    <div>
                      <Label className="capitalize">{key.replace(/([A-Z])/g, ' $1')}</Label>
                      <p className="text-sm text-muted-foreground">
                        {key === "email" && "Receive email notifications"}
                        {key === "push" && "Receive push notifications in browser"}
                        {key === "costAlerts" && "Alert when cost thresholds are reached"}
                        {key === "healthAlerts" && "Alert when system health degrades"}
                        {key === "governanceAlerts" && "Alert on governance events"}
                        {key === "weeklyDigest" && "Receive weekly summary email"}
                      </p>
                    </div>
                    <Switch checked={value} onCheckedChange={c => setNotifications(n => ({ ...n, [key]: c }))} />
                  </div>
                ))}
              </div>
              <Button onClick={() => handleSave("Notifications")} disabled={saving}>
                {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                Save Changes
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Tab */}
        <TabsContent value="security">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Two-Factor Authentication</CardTitle>
                <CardDescription>Add an extra layer of security to your account</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Enable 2FA</Label>
                    <p className="text-sm text-muted-foreground">Require authenticator app code on login</p>
                  </div>
                  <Switch checked={security.twoFactor} onCheckedChange={c => setSecurity(s => ({ ...s, twoFactor: c }))} />
                </div>
                <div className="p-4 bg-muted/50 rounded-lg text-sm text-muted-foreground">
                  2FA is currently <strong>{security.twoFactor ? "enabled" : "disabled"}</strong>. 
                  {security.twoFactor ? "You'll need your authenticator app to log in." : "Enable 2FA to require a verification code from your authenticator app."}
                </div>
                <Button onClick={() => handleSave("Security")} disabled={saving} variant={security.twoFactor ? "outline" : "default"}>
                  {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                  {security.twoFactor ? "Disable 2FA" : "Enable 2FA"}
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Session & API Keys</CardTitle>
                <CardDescription>Configure session timeouts and API key rotation</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Session Timeout (minutes)</Label>
                  <Input type="number" value={security.sessionTimeout} onChange={e => setSecurity(s => ({ ...s, sessionTimeout: parseInt(e.target.value) }))} min="15" max="480" />
                  <p className="text-sm text-muted-foreground">Automatically log out after inactivity</p>
                </div>
                <div className="space-y-2">
                  <Label>API Key Rotation (days)</Label>
                  <Input type="number" value={security.apiKeyRotation} onChange={e => setSecurity(s => ({ ...s, apiKeyRotation: parseInt(e.target.value) }))} min="30" max="365" />
                  <p className="text-sm text-muted-foreground">Recommended: 90 days for production keys</p>
                </div>
                <Button onClick={() => handleSave("Security")} disabled={saving}>
                  {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                  Save Changes
                </Button>
              </CardContent>
            </Card>

            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>Danger Zone</CardTitle>
                <CardDescription>Irreversible actions</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between p-4 border rounded-lg bg-red-50">
                  <div>
                    <p className="font-medium text-red-900">Delete Account</p>
                    <p className="text-sm text-red-700">Permanently delete your account and all associated data</p>
                  </div>
                  <Button variant="destructive">Delete Account</Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Workspaces Tab */}
        <TabsContent value="workspaces">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Workspace Management</CardTitle>
                  <CardDescription>Manage your workspaces and their configurations</CardDescription>
                </div>
                <Button variant="outline"><Database className="h-4 w-4 mr-2" />Create Workspace</Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {workspaces.map(ws => (
                  <div key={ws} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-4">
                      <div className="p-2 bg-primary/10 rounded-lg">
                        <Database className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <p className="font-medium capitalize">{ws}</p>
                        <p className="text-sm text-muted-foreground">
                          {ws === "prod" && "Production environment"}
                          {ws === "staging" && "Staging environment"}
                          {ws === "dev" && "Development environment"}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={ws === "prod" ? "default" : ws === "staging" ? "secondary" : "outline"}>
                        {ws === "prod" ? "Active" : ws === "staging" ? "Staging" : "Development"}
                      </Badge>
                      <Button variant="ghost" size="icon"><Settings className="h-4 w-4" /></Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Toaster />
    </div>
  );
}