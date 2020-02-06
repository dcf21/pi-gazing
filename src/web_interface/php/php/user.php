<?php

// user.php
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2015-2020 Dominic Ford.

// This file is part of Pi Gazing.

// Pi Gazing is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Pi Gazing is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Pi Gazing.  If not, see <http://www.gnu.org/licenses/>.
// -------------------------------------------------

class userSession
{
    public $username;
    public $name;
    public $roles;
    public $profilePic;
    public $profileText;
    public $refused;
    private $key;

    public function __construct()
    {
        global $const;

        $this->userId = null;
        $this->username = null;
        $this->name = null;
        $this->roles = [];
        $this->profilePic = null;
        $this->profileText = null;
        $this->refused = false;

        // Make IP address integer
        if (!array_key_exists('REMOTE_ADDR', $_SERVER)) $ipAddr = 0;
        else $ipAddr = $_SERVER['REMOTE_ADDR'];
        $ipBits = explode(".", $ipAddr);
        if (count($ipBits) != 4) $ipBits = [0, 0, 0, 0];
        $networkAddr = (16777216 * intval($ipBits[0])) + (65536 * intval($ipBits[1])) + (256 * intval($ipBits[2])) + intval($ipBits[3]);

        // Settings
        $this->key = "Aew3SheeEitei8ph";
        $this->lifetime = 3600 * 3;
        $time = time();

        // Check for valid session cookie
        if (isset($_COOKIE[$this->key])) {
            $cookie = $_COOKIE[$this->key];
            $cookieLen = strlen($cookie);
            if ($cookieLen == 32) {
                $stmt = $const->db->prepare("SELECT * FROM archive_user_sessions WHERE cookie=:c;");
                $stmt->bindParam(':c', $c, PDO::PARAM_STR, $cookieLen);
                $stmt->execute(['c' => $cookie]);
                $sessionList = $stmt->fetchAll(PDO::FETCH_ASSOC);
                if (count($sessionList) == 1) {
                    $session = $sessionList[0];
                    if ((!$session['logOut']) && ($session['lastSeen'] > $time - $this->lifetime)) {
                        $this->userId = $session['userId'];
                    }
                }
            }
        }

        // Check for valid login
        if (!$this->username) {
            if (isset($_POST['un']) && isset($_POST['pw'])) {
                $username = $_POST['un'];
                $secret = $_POST['pw'];
                $stmt = $const->db->prepare("SELECT * FROM archive_users WHERE userId=:u;");
                $stmt->bindParam(':u', $u, PDO::PARAM_STR, strlen($username));
                $stmt->execute(['u' => $username]);
                $userList = $stmt->fetchAll(PDO::FETCH_ASSOC);
                if ((count($userList) == 1) && password_verify($secret, $userList[0]['pwHash'])) {
                    $this->userId = $userList[0]['uid'];
                    $bytes = openssl_random_pseudo_bytes(16);
                    $cookieVal = bin2hex($bytes);
                    setcookie($this->key, $cookieVal, $time + $this->lifetime, "/");
                    $stmt = $const->db->prepare("
INSERT INTO archive_user_sessions (userId, logIn, lastSeen, ip, cookie) VALUES (:u,:t,:t,:i,:c);");
                    $stmt->bindParam(':u', $c, PDO::PARAM_INT);
                    $stmt->bindParam(':i', $i, PDO::PARAM_INT);
                    $stmt->bindParam(':i', $t, PDO::PARAM_STR, 64);
                    $stmt->bindParam(':c', $c, PDO::PARAM_STR, 32);
                    $stmt->execute(['u' => $this->userId, 't' => $time, 'i' => $networkAddr, 'c' => $cookieVal]);
                }
                else
                {
                    $this->refused = true;
                }
            }
        }

        // Look up information about user
        if ($this->userId) {
            $stmt = $const->db->prepare("SELECT * FROM archive_users WHERE uid=:u;");
            $stmt->bindParam(':u', $u, PDO::PARAM_INT);
            $stmt->execute(['u' => $this->userId]);
            $userList = $stmt->fetchAll(PDO::FETCH_ASSOC);
            if (count($userList) == 1) {
                $user = $userList[0];
                $this->username = $user['userId'];
                $stmt = $const->db->prepare("
SELECT r.name FROM archive_user_roles ur
INNER JOIN archive_roles r ON ur.roleId=r.uid
WHERE ur.userId=:u;");
                $stmt->bindParam(':u', $u, PDO::PARAM_INT);
                $stmt->execute(['u' => $this->userId]);
                $roleList = $stmt->fetchAll(PDO::FETCH_ASSOC);
                foreach ($roleList as $role) $this->roles[] = $role['name'];
            }
        }
    }

    public function logOut()
    {
        global $const;
        $time = time();
        if (isset($_COOKIE[$this->key])) {
            $cookie = $_COOKIE[$this->key];
            $cookieLen = strlen($cookie);
            if ($cookieLen == 32) {
                $stmt = $const->db->prepare("
UPDATE archive_user_sessions SET logOut=:t WHERE cookie=:c AND logOut IS NULL;");
                $stmt->bindParam(':c', $c, PDO::PARAM_STR, $cookieLen);
                $stmt->bindParam(':t', $t, PDO::PARAM_STR, 64);
                $stmt->execute(['t' => $time, 'c' => $cookie]);
            }
        }
        setcookie($this->key, "", time() - 10, "/");
    }

    public function cron()
    {
        global $const;
        $time = time();
        $tmin = $time - $this->lifetime;
        $stmt = $const->db->prepare("
UPDATE archive_user_sessions SET logOut=:t
WHERE lastSeen<userId=:tmin;");
        $stmt->bindParam(':t', $t, PDO::PARAM_STR, 64);
        $stmt->bindParam(':tmin', $t, PDO::PARAM_STR, 64);
        $stmt->execute(['t' => $time, 'tmin' => $tmin]);
    }
}


$user = new userSession();
